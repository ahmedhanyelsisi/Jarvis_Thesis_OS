from jarvis import Jarvis


def main():

    print(
        "Jarvis Thesis OS v0.3"
    )

    print(
        "Multi-Agent Kernel Initialized"
    )

    jarvis = Jarvis()


    response = jarvis.process_request(
        "Create methodology diagram"
    )


    print(response)


if __name__ == "__main__":
    main()
