import subprocess
import time

def main():
    with open('inputs.txt', 'r') as file:
        lines = file.readlines()

    for line in lines:
        line = line.strip()
        try:
            print('Fuzzing with input: ' + line)
            subprocess.check_output(f"python3 target_program.py {line}", shell=True)
            time.sleep(.5)
        except subprocess.CalledProcessError as e:
            print(f"Crashed with input: {line}")
            break  # Stop fuzzing after a crash

if __name__ == "__main__":
    main()
