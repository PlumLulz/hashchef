import re
import time
import json
import shlex
import os.path
import argparse
import requests
import threading
import subprocess
from datetime import datetime

# Argparse details/handling
epilog_text = '''
Example Usage:
	Preview Hashcat commands for each step:
	python3 %(prog)s.py hashfile.txt cracked.txt 0 hc_md5.recipe -preview

	Start running recipe with verbose output:
	python3 %(prog)s.py hashfile.txt cracked.txt 0 hc_md5.recipe -verbose
'''
parse = argparse.ArgumentParser(prog='hashchef', description='Lightweight Hashcat wrapper to automate workflows', epilog=epilog_text, formatter_class=argparse.RawDescriptionHelpFormatter)
parse.add_argument('infile', help='Hashlist file', type=str)
parse.add_argument('outfile', help='Output file for cracked hashes', type=str)
parse.add_argument('mode', help='Hashcat hash mode', type=int)
parse.add_argument('recipe', help='Hashchef recipe file', type=str)
parse.add_argument('-verbose', help='Verbose console output', action='store_true')
parse.add_argument('-preview', help='Preview Hashcat command for steps', action='store_true')
args = parse.parse_args()

# Header / Version
version = "v1.1 Beta"
header = f"""
                                                   .--,--.
                                                   `.  ,.'
                                                    |___|
██  ██  ▄▄▄   ▄▄▄▄ ▄▄ ▄▄  ▄▄▄▄ ▄▄ ▄▄ ▄▄▄▄▄ ▄▄▄▄▄    :o o:
██████ ██▀██ ███▄▄ ██▄██ ██▀▀▀ ██▄██ ██▄▄  ██▄▄    _`~^~'_
██  ██ ██▀██ ▄▄██▀ ██ ██ ▀████ ██ ██ ██▄▄▄ ██    /'   ^   `\\
{version}
"""
print(header)

# Functions

# Hashes.com upload API integration
def start_monitor(upload_freq, api_key, outfile, algid):

	# Log of upload details
	def upload_log(hash_count, response):
		current_timestamp = datetime.now().strftime("%m-%d-%Y %H:%M:%S")
		log = "[%s] Attempted to upload %s hashes to hashes.com. Server response: %s\n" % (current_timestamp, str(hash_count), response)
		with open("hashchef.log", "a+") as logfile:
			logfile.write(log)

	# Upload function for hashes.com API
	def upload(upload_file, line_count):
		uploadurl =  "https://hashes.com/en/api/founds"
		data = {"key": api_key, "algo": algid}
		file = {"userfile": open(upload_file, "rb")}
		post = requests.post(uploadurl, files=file, data=data).json()
		if post["success"] == True:
			upload_log(line_count, "File successfully uploaded.")
		else:
			upload_log(line_count, "Failed to upload file.")

	# Monitor outfile for new cracks and upload to hashes.com via API
	def outfile_monitor():
		monitor_start_time = time.time()
		outfile_lastmtime = None
		upload_history = []
		while True:
			if monitor != True:
				break
			else:
				monitor_elapsed = time.time() - monitor_start_time
				if monitor_elapsed >= upload_freq:
					# Check if outfile exists yet
					if os.path.isfile(outfile) == True:
						# Check if file has been modified via mtimes since last interval
						# This helps prevent reading the file every interval if not needed
						if outfile_lastmtime == None:
							# First time checking outfile. All cracks will be uploaded and stored.
							# Create a list of hashes being uploaded and line count before sending to upload.
							with open(outfile, "r") as of:
								for line in of:
									upload_history.append(line.rstrip())

							# Upload cracks to hashes.com
							upload(outfile, len(upload_history))

							# Update last outfile mtime check
							outfile_lastmtime = os.path.getmtime(outfile)
						elif outfile_lastmtime != os.path.getmtime(outfile):
							# File has been changed since last check
							# In order to upload the smallest amount of data we will read file to get only new lines. 
							# We will also put new cracks in a temp file to upload. This will keep the integrity of the original outfile intact. 
							new_cracks = []
							with open(outfile, "r") as of:
								for line in of:
									if line.rstrip() not in upload_history:
										# New crack, add to new_cracks list and upload_history list
										new_cracks.append(line.rstrip())
										upload_history.append(line.rstrip())
							
							# Create temp upload file for new cracks to maintain integrity of original outfile
							with open("temp_upload.txt", "w+") as tf:
								tf.write("\n".join(new_cracks))

							# Upload new cracks to hashes.com
							upload("temp_upload.txt", len(new_cracks))

							# Update last outfile mtime check
							outfile_lastmtime = os.path.getmtime(outfile)
						else:
							# File has not changed since last check
							# Update last outfile mtime check
							outfile_lastmtime = os.path.getmtime(outfile)
					
					# Reset time
					monitor_start_time = time.time()

	# This thread will not be joined to allow the script to continue while this runs in background
	t1 = threading.Thread(target=outfile_monitor)
	t1.start()

# Hashcat subprocess execution and output handling functions
def execute_hashcat(command, excluded, bypass_timeout, step_timeout, verbose):
	step_start_time = time.time()
	p = subprocess.Popen(shlex.split(command), stderr=subprocess.PIPE, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

	# Read and process Hashcat output
	def hashcat_output(step_start_time):
		while True:
			output = p.stdout.readline()

			# End of output
			if len(output) < 1:
				p.terminate()
				p.wait()
				break
			else:
				# Check if step timeout has been reached
				if step_timeout != None:
					step_elapsed = time.time() - step_start_time
					if step_elapsed >= 60 * step_timeout:
						step_start_time = time.time()
						p.stdin.write(("q\n").encode())
						p.stdin.flush()

				# Check if wordlist is excluded in -a 0 attacks
				# Also check if bypass timeout has been reached
				current_list = re.search('Guess.Base', output.decode().rstrip())
				bypass_elapsed = re.search('Time.Started', output.decode().rstrip())
				if current_list != None:
					if excluded != None:
						clist = output.decode().rstrip()
						clist = clist[clist.find("(")+1:clist.find(")")].split("/")[-1]
						if clist in excluded:
							# Remove list from excluded once it is bypassed. This prevents multiple bypass requests being sent.
							excluded.remove(clist)
							p.stdin.write(("b\n").encode())
							p.stdin.flush()
				elif bypass_elapsed != None:
					if bypass_timeout != None:
						belapsed = output.decode().rstrip()
						belapsed = belapsed[belapsed.find("(")+1:belapsed.find(")")].split("/")[-1].split(",")
						if len(belapsed) == 2:
							# Hashcat changes time format once an hour or more of runtime has passed
							# Due to this change in format some logic needs to be done to handle bypass timeouts
							if "hour" in belapsed[0]:
								# Hour of more of runtime
								bhours = re.findall(r'\d+', belapsed[0])[0]
								bmins = re.findall(r'\d+', belapsed[1])[0]
								bmins = int(bhours) * 60 + int(bmins)
							elif "min" in belapsed[0]:
								# Less than an hour of runtime
								bmins = re.findall(r'\d+', belapsed[0])[0]
							if int(bmins) >= bypass_timeout:
								p.stdin.write(("b\n").encode())
								p.stdin.flush()
				
				# Handle verbose/non-verbose console printing
				if verbose == True:
					print(output.decode().rstrip())
				else:
					current_mask = re.search('Guess.Mask', output.decode().rstrip())
					recover_status = re.search('Recovered', output.decode().rstrip())
					time_started = re.search('Time.Started', output.decode().rstrip())
					estimated_time = re.search('Time.Estimated', output.decode().rstrip())
					hardware_mon = re.search('Hardware.Mon', output.decode().rstrip())
					if current_list != None:
						clist = output.decode().rstrip()
						print(clist)
					elif current_mask != None:
						cmask = output.decode().rstrip()
						print(cmask)
					elif time_started != None:
						tstarted = output.decode().rstrip()
						print(tstarted)
					elif estimated_time != None:
						etime = output.decode().rstrip()
						print(etime)
					elif recover_status != None:
						rstatus = output.decode().rstrip()
						print(rstatus)
						# Clear last results to prevent console clutter during non verbose output
						print("\033[%sF\033[J" % (4), end="")
	
	# Start to read Hashcat output, this thread will get joined to wait for it to finish before moving on.
	t0 = threading.Thread(target=hashcat_output, kwargs={"step_start_time": step_start_time})
	t0.start()
	t0.join()
	return

# Open and start or preview recipe
try:
	with open(args.recipe, "r") as recipe:
		try:
			recipe = json.loads(recipe.read())
			recipe_name = recipe['recipe_name']
			recipe_steps = recipe['recipe_steps']
			hashes_api = recipe['hashes_api']

			# Start monitoring outfile for new cracks to upload to hashes.com in background before starting recipe.
			# Only monitor when starting a recipe and not previewing. 
			if hashes_api != None and args.preview == False:
				print("Starting monitor for new cracked hashes for hashes.com API integration.\n")
				monitor = True
				api_key = hashes_api['api_key']
				upload_freq = hashes_api['upload_frequency']
				start_monitor(upload_freq, api_key, args.outfile, args.mode)

			print("Starting recipe '%s'\n" % (recipe_name))
			for step in recipe_steps:
				step_name = recipe_steps[step]['step_name']
				attack_mode = recipe_steps[step]['attack_mode']
				wordlist = recipe_steps[step]['wordlist']
				mask = " ".join(recipe_steps[step]['mask']) if isinstance(recipe_steps[step]['mask'], list) else recipe_steps[step]['mask']
				exclude = recipe_steps[step]['exclude']
				bypass_timeout = recipe_steps[step]['bypass_timeout']
				step_timeout = recipe_steps[step]['step_timeout']
				optflags = recipe_steps[step]['optflags']
				aopt = " ".join(wordlist) if attack_mode == 0 else mask
				hc_command = "hashcat -m %s -a %s %s %s --outfile %s %s --status --status-timer=1" % (args.mode, attack_mode, args.infile, aopt, args.outfile, " ".join(optflags))

				if args.preview == True:
					print("Previewing Hashcat command for step '%s'" % (step_name))
					print(hc_command+"\n")
				else:
					print("Starting step '%s'" % (step_name))
					print("Attack mode: %s (%s)" % (attack_mode, aopt))
					if attack_mode == 0:
						if exclude != None:
							print("Excluded wordlists: %s" % (", ".join(exclude)))
					print("Bypass timeoout: %s" % (bypass_timeout))
					print("Step timeout: %s" % (step_timeout))
					print("Optional hashcat flags: %s" % (", ".join(optflags)))
					execute_hashcat(hc_command, exclude, bypass_timeout, step_timeout, args.verbose)
					print("Completed step '%s'\n" % (step_name))

			# Steps completed. Stop monitoring for new cracks if started.
			if hashes_api != None:
				monitor = False
		except Exception as e:
			print("An error occurred while parsing recipe file. Please check recipe file format.")
			print("Error: %s" % (e))
except Exception as e:
	print("An error occurred while loading recipe file.")
	print("Error: %s" % (e))
