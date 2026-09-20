def analyze_novelty(topic: str):

    topic_clean = topic.strip()

    topic_lower = topic_clean.lower()


    # --------------------------------------------------
    # Research Area Detection
    # --------------------------------------------------

    if any(
        keyword in topic_lower
        for keyword in [
            "computer vision",
            "image processing",
            "object detection",
            "yolo",
            "cnn"
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


    # --------------------------------------------------
    # Basic Novelty Heuristic
    # --------------------------------------------------

    novelty_score = 50.0


    specific_terms = [

        "real-time",
        "real time",
        "edge",
        "mobile",
        "lightweight",
        "explainable",
        "privacy",
        "federated",
        "multimodal",
        "transformer",
        "optimization"

    ]


    matched_terms = [

        term
        for term in specific_terms
        if term in topic_lower

    ]


    novelty_score += len(matched_terms) * 5


    if len(topic_clean.split()) > 10:

        novelty_score += 5


    novelty_score = min(
        novelty_score,
        100.0
    )


    # --------------------------------------------------
    # Novelty Level
    # --------------------------------------------------

    if novelty_score >= 75:

        novelty_level = "Potentially Novel"

    elif novelty_score >= 55:

        novelty_level = "Moderate Novelty"

    else:

        novelty_level = "Low Novelty"


    # --------------------------------------------------
    # Potential Research Gap
    # --------------------------------------------------

    if matched_terms:

        potential_gap = (

            "The topic includes specialized research "
            "dimensions. A literature review is required "
            "to determine whether these dimensions have "
            "already been sufficiently studied."

        )

    else:

        potential_gap = (

            "The topic is based on an established research "
            "area. A specific research gap should be "
            "identified through comparison with existing "
            "literature."

        )


    # --------------------------------------------------
    # Recommendation
    # --------------------------------------------------

    recommendation = (

        "Search recent research papers and compare "
        "datasets, methods, performance metrics, and "
        "limitations before claiming novelty."

    )


    return {

        "topic": topic_clean,

        "research_area": research_area,

        "novelty_level": novelty_level,

        "novelty_score": novelty_score,

        "potential_gap": potential_gap,

        "recommendation": recommendation

    }