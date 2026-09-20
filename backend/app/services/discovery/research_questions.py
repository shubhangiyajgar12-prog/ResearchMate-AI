def generate_research_questions(
    topic: str,
    research_gaps: list[str]
):

    topic_clean = topic.strip()

    topic_lower = topic_clean.lower()


    # ==================================================
    # RESEARCH AREA
    # ==================================================

    if any(
        keyword in topic_lower
        for keyword in [
            "computer vision",
            "image processing",
            "object detection",
            "yolo",
            "cnn",
            "image"
        ]
    ):

        research_area = (
            "Computer Vision / Deep Learning"
        )


    elif any(
        keyword in topic_lower
        for keyword in [
            "machine learning",
            "deep learning",
            "artificial intelligence",
            "ai"
        ]
    ):

        research_area = (
            "Artificial Intelligence / Machine Learning"
        )


    elif any(
        keyword in topic_lower
        for keyword in [
            "blockchain",
            "smart contract",
            "defi"
        ]
    ):

        research_area = "Blockchain"


    elif any(
        keyword in topic_lower
        for keyword in [
            "cybersecurity",
            "cyber security",
            "malware",
            "intrusion"
        ]
    ):

        research_area = "Cybersecurity"


    else:

        research_area = "General Computer Science"


    # ==================================================
    # RESEARCH QUESTIONS
    # ==================================================

    research_questions = []


    # General research question

    research_questions.append(

        f"How can {topic_clean} be effectively "
        f"developed and evaluated?"

    )


    # Performance question

    research_questions.append(

        f"How does the proposed approach perform "
        f"compared with existing methods for "
        f"{topic_clean}?"

    )


    # Dataset / generalization question

    research_questions.append(

        f"How do dataset characteristics and "
        f"environmental conditions affect the "
        f"performance of {topic_clean}?"

    )


    # Real-time question

    if (
        "real-time" in topic_lower
        or "real time" in topic_lower
    ):

        research_questions.append(

            "What is the impact of real-time deployment "
            "requirements on accuracy, latency, and "
            "computational efficiency?"

        )


    # Explainability question

    if not any(
        keyword in topic_lower
        for keyword in [
            "explainable",
            "explainability",
            "interpretable"
        ]
    ):

        research_questions.append(

            "Can explainability techniques improve the "
            "interpretability and trustworthiness of "
            "the proposed approach?"

        )


    # ==================================================
    # HYPOTHESIS
    # ==================================================

    hypothesis = (

        f"A research approach designed for {topic_clean} "
        f"can improve relevant performance measures "
        f"when compared with suitable existing methods, "
        f"subject to empirical validation."

    )


    # ==================================================
    # VARIABLES
    # ==================================================

    variables = [

        "Independent Variable: Proposed methodology",

        "Dependent Variable: Model performance",

        "Evaluation Metrics: Accuracy, Precision, Recall, F1-score",

        "Dataset: Research-specific dataset",

        "Comparison Baseline: Existing state-of-the-art methods"

    ]


    # ==================================================
    # RESEARCH DIRECTION
    # ==================================================

    research_direction = (

        "Evaluate the proposed approach using appropriate "
        "datasets and metrics, compare it with existing "
        "methods, and investigate the identified research "
        "gaps through controlled experiments."

    )


    return {

        "topic": topic_clean,

        "research_area": research_area,

        "research_questions": research_questions,

        "hypothesis": hypothesis,

        "variables": variables,

        "research_direction": research_direction

    }