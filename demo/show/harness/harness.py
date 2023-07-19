import subprocess
import time
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 script.py <filename>")
        return
    filename = sys.argv[1]
    with open(filename, 'r') as file:
        lines = file.readlines()

    crash_found = False  

    for line in lines:
        line = line.strip()
        try:
            print('Fuzzing with input: ' + line)
            subprocess.check_output(f"python3 target_program.py {line}", shell=True)
            time.sleep(.5)
        except subprocess.CalledProcessError as e:
            print(f"Crashed with input: {line}")
            crash_found = True
            break  # Stop fuzzing after a crash
    if not crash_found:
        print("Done fuzzing, no crashes found!")

if __name__ == "__main__":
    main()
