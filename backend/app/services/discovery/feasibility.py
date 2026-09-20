def analyze_feasibility(topic: str):

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

        research_area = "Computer Vision / Deep Learning"


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
    # INITIAL SCORE
    # ==================================================

    score = 60.0


    # ==================================================
    # DATASET FEASIBILITY
    # ==================================================

    dataset_keywords = [
        "detection",
        "classification",
        "recognition",
        "prediction",
        "image",
        "text",
        "sentiment"
    ]


    if any(
        keyword in topic_lower
        for keyword in dataset_keywords
    ):

        dataset_feasibility = "High"

        score += 10

    else:

        dataset_feasibility = "Moderate"


    # ==================================================
    # COMPUTATIONAL FEASIBILITY
    # ==================================================

    heavy_computation_keywords = [
        "large language model",
        "llm",
        "transformer",
        "generative ai",
        "multimodal",
        "video processing"
    ]


    if any(
        keyword in topic_lower
        for keyword in heavy_computation_keywords
    ):

        computational_feasibility = "Moderate"

        score -= 5

    elif any(
        keyword in topic_lower
        for keyword in [
            "machine learning",
            "deep learning",
            "yolo",
            "cnn"
        ]
    ):

        computational_feasibility = "Moderate to High"

        score += 5

    else:

        computational_feasibility = "High"


    # ==================================================
    # IMPLEMENTATION COMPLEXITY
    # ==================================================

    if any(
        keyword in topic_lower
        for keyword in [
            "real-time",
            "real time",
            "multimodal",
            "distributed",
            "federated",
            "blockchain"
        ]
    ):

        implementation_complexity = "High"

        score -= 10


    elif any(
        keyword in topic_lower
        for keyword in [
            "machine learning",
            "deep learning",
            "computer vision",
            "ai"
        ]
    ):

        implementation_complexity = "Moderate"

    else:

        implementation_complexity = "Low"


    # ==================================================
    # EVALUATION FEASIBILITY
    # ==================================================

    evaluation_keywords = [
        "detection",
        "classification",
        "prediction",
        "recognition",
        "machine learning",
        "deep learning"
    ]


    if any(
        keyword in topic_lower
        for keyword in evaluation_keywords
    ):

        evaluation_feasibility = "High"

        score += 5

    else:

        evaluation_feasibility = "Moderate"


    # ==================================================
    # LIMIT SCORE
    # ==================================================

    score = max(
        0.0,
        min(score, 100.0)
    )


    # ==================================================
    # OVERALL FEASIBILITY
    # ==================================================

    if score >= 75:

        overall_feasibility = "Highly Feasible"

    elif score >= 55:

        overall_feasibility = "Potentially Feasible"

    else:

        overall_feasibility = "Requires Further Planning"


    # ==================================================
    # CHALLENGES
    # ==================================================

    challenges = []


    if dataset_feasibility != "High":

        challenges.append(
            "Finding a sufficiently large and representative "
            "dataset may be challenging."
        )


    if computational_feasibility != "High":

        challenges.append(
            "Computational resources may be required for "
            "training and experimentation."
        )


    if implementation_complexity == "High":

        challenges.append(
            "The proposed methodology may require significant "
            "implementation effort."
        )


    challenges.append(
        "Performance should be evaluated using appropriate "
        "baselines and research metrics."
    )


    # ==================================================
    # RECOMMENDATIONS
    # ==================================================

    recommendations = [

        "Verify dataset availability before finalizing the methodology.",

        "Define measurable evaluation metrics.",

        "Start with a baseline implementation.",

        "Compare the proposed method with existing approaches.",

        "Estimate computational requirements before large-scale experiments."

    ]


    # ==================================================
    # RESPONSE
    # ==================================================

    return {

        "topic": topic_clean,

        "research_area": research_area,

        "dataset_feasibility": dataset_feasibility,

        "computational_feasibility": computational_feasibility,

        "implementation_complexity": implementation_complexity,

        "evaluation_feasibility": evaluation_feasibility,

        "overall_feasibility": overall_feasibility,

        "feasibility_score": score,

        "challenges": challenges,

        "recommendations": recommendations

    }