import sys

sys.path.append("01_CORE_KERNEL")

from task_router import TaskRouter


def test_literature_routing():

    router = TaskRouter()

    result = router.route(
        "Analyze literature review"
    )

    assert result == "literature_agent"


if __name__ == "__main__":

    test_literature_routing()

    print(
        "Kernel test passed successfully."
    )
