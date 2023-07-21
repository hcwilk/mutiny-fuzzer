import random

def main():
    while True:
        user_input = input("Enter your input: ")
        
        if user_input == 'whateveryoudodonttypethis':
            print("CRASHED!")
            break
        
        else:
            messages = ["Success!"]
            print(random.choice(messages))

if __name__ == "__main__":
    main()
