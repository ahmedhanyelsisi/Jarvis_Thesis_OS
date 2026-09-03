class TaskRouter:


    def __init__(self):

        self.rules = {


            # Specific research tasks first

            "literature review": "literature_agent",

            "literature": "literature_agent",

            "research paper": "literature_agent",

            "paper": "literature_agent",



            # Writing

            "write": "thesis_writer_agent",

            "chapter": "thesis_writer_agent",



            # LaTeX

            "latex": "latex_agent",

            "equation": "latex_agent",



            # Citation

            "citation": "citation_agent",

            "reference": "citation_agent",

            "bibliography": "citation_agent",



            # Diagram

            "diagram": "diagram_agent",

            "figure": "diagram_agent",

            "visual": "diagram_agent",



            # Review last

            "review": "reviewer_agent",

            "check": "reviewer_agent"

        }



    def route(self, request):

        request = request.lower()


        for keyword, agent in self.rules.items():

            if keyword in request:

                return agent


        return "thesis_writer_agent"
