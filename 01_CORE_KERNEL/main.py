from jarvis import Jarvis


def main():

    print("================================")
    print(" Jarvis Thesis OS v0.1")
    print(" Core Kernel Initialized")
    print("================================")

    jarvis = Jarvis()

    request = input("\nUser: ")

    response = jarvis.process_request(request)

    print("\nJarvis:")
    print(response)


if __name__ == "__main__":
    main()

