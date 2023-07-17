import random

def main():
    while True:
        user_input = raw_input("Enter your input: ")  # use raw_input in Python 2
        
        if user_input == 'whateveryoudodonttypethis':
            print("CRASHED!")
            break
        
        else:
            messages = ["Success!"]
            print(random.choice(messages))

if __name__ == "__main__":
    main()
