def validate_topic(topic: str):

    topic_clean = topic.strip()

    words = topic_clean.split()

    # Specificity
    if len(words) <= 5:
        specificity = "Needs More Specificity"
    elif len(words) <= 10:
        specificity = "Moderately Specific"
    else:
        specificity = "Highly Specific"

    # Research field detection
    topic_lower = topic_clean.lower()

    if any(
        word in topic_lower
        for word in [
            "ai",
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "neural network"
        ]
    ):
        research_field = "Artificial Intelligence / Machine Learning"

    elif any(
        word in topic_lower
        for word in [
            "blockchain",
            "smart contract",
            "defi"
        ]
    ):
        research_field = "Blockchain"

    elif any(
        word in topic_lower
        for word in [
            "cybersecurity",
            "cyber security",
            "intrusion",
            "malware"
        ]
    ):
        research_field = "Cybersecurity"

    elif any(
        word in topic_lower
        for word in [
            "iot",
            "internet of things",
            "sensor"
        ]
    ):
        research_field = "Internet of Things"

    else:
        research_field = "General Computer Science"

    # Feasibility
    if len(topic_clean) >= 20:
        feasibility = "Potentially Feasible"
    else:
        feasibility = "Requires Further Definition"

    # Keywords
    keywords = [
        word.strip(".,!?")
        for word in words
        if len(word) > 3
    ]

    validation_summary = (
        f"The topic appears to be {specificity.lower()} "
        f"and belongs primarily to the {research_field} domain. "
        f"Further literature analysis is required to evaluate "
        f"research novelty and research gaps."
    )

    return {
        "topic": topic_clean,
        "research_field": research_field,
        "specificity": specificity,
        "feasibility": feasibility,
        "keywords": keywords,
        "validation_summary": validation_summary
    }