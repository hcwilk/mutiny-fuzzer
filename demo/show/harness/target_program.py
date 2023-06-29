import sys

def main():
    user_input = sys.argv[1]
    if user_input == 'whateveryoudonttypethis':
        raise Exception('CRASHED')
    else:
        print('Call Successful!!')

if __name__ == "__main__":
    main()
