import sys
import os


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)


CORE_PATH = os.path.join(
    PROJECT_ROOT,
    "01_CORE_KERNEL"
)


sys.path.insert(
    0,
    CORE_PATH
)


from task_router import TaskRouter



def test_literature_routing():

    router = TaskRouter()

    result = router.route(
        "Analyze literature review"
    )

    print("Router returned:", result)

    assert result == "literature_agent"



if __name__ == "__main__":

    test_literature_routing()

    print(
        "Kernel test passed successfully."
    )
