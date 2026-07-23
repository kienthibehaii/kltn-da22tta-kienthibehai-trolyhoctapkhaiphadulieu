# educational_engine/analogy_database.py
"""
Analogy Database - Pre-Built Domain-Specific Analogies

Hardcoded analogies for common ML/CS concepts at different difficulty levels.
NO LLM generation - all analogies pre-built by domain experts.

NO LLM CALLS - Analogies loaded once at startup.
"""

ANALOGY_DATABASE = {
    # Decision Trees
    'decision_tree': {
        'beginner': "It's like a flowchart of yes/no questions that narrows down to a decision. Like asking 'Is it alive?' → 'Does it have fur?' → 'Does it meow?' to identify an animal.",
        'intermediate': "Binary tree structure where each node asks a question that partitions data. Leaf nodes represent final decisions or classifications.",
        'expert': "Tree-based model using recursive binary partitioning with information gain (Gini impurity or entropy) optimization. Each split maximizes information gain."
    },

    # Clustering
    'clustering': {
        'beginner': "It's like sorting students into groups based on study habits WITHOUT telling the algorithm what groups to create. The algorithm finds natural groupings on its own.",
        'intermediate': "Unsupervised learning algorithm partitioning data into k clusters by minimizing intra-cluster distance and maximizing inter-cluster distance.",
        'expert': "Distance-based or density-based partitioning (k-means, hierarchical, DBSCAN) optimizing objective functions like squared Euclidean distance or silhouette coefficient."
    },

    # Regression
    'regression': {
        'beginner': "It's like learning the relationship between hours studied and test score. You draw a line through your past data, then use that line to predict future scores.",
        'intermediate': "Supervised learning predicting continuous values by fitting a function to historical (X, y) pairs. Linear regression uses y = mx + b.",
        'expert': "Supervised learning minimizing loss functions (MSE, L1, etc.) through gradient descent. Regularization (L1, L2) prevents overfitting."
    },

    # Classification
    'classification': {
        'beginner': "It's like email spam detection. You look at past emails (labeled spam or not), learn patterns, then use those patterns to classify new emails.",
        'intermediate': "Supervised learning assigning items to predefined classes based on learned decision boundaries from labeled training data.",
        'expert': "Supervised learning with discrete output space, optimizing class probability estimation through log loss, cross-entropy, or hinge loss."
    },

    # Neural Networks
    'neural_network': {
        'beginner': "It's like how your brain learns. You show it examples, it adjusts internal connections, and gradually learns to recognize patterns. Like learning to recognize dogs by seeing many dogs.",
        'intermediate': "Multi-layer perceptron with neurons connected by weighted edges, trained via backpropagation. Each layer learns progressively more complex features.",
        'expert': "Non-linear function approximator with differentiable activation functions, trained via SGD and backpropagation. Universal approximator with sufficient hidden units."
    },

    # Deep Learning
    'deep_learning': {
        'beginner': "Neural networks with many layers that learn features automatically. Like a student progressively understanding complex topics through many simple lessons.",
        'intermediate': "Neural networks with 3+ hidden layers. Each layer learns increasingly abstract representations of input data.",
        'expert': "Deep architectures with multiple non-linear transformations enabling learning of hierarchical representations. Requires careful initialization and regularization."
    },

    # Machine Learning
    'machine_learning': {
        'beginner': "It's about making programs that learn from examples instead of being programmed with rules. Like learning to identify dogs by seeing many dogs, not by being told 'dogs have 4 legs'.",
        'intermediate': "Supervised, unsupervised, and reinforcement learning paradigms for extracting patterns from data without explicit programming.",
        'expert': "Statistical learning theory with generalization bounds (VC dimension, PAC learning) and model selection via cross-validation."
    },

    # Recursion
    'recursion': {
        'beginner': "It's like a Russian nesting doll (matryoshka). You open the first doll to find a smaller doll inside, which contains another doll, until you reach the tiniest doll (base case).",
        'intermediate': "Function calling itself with a simpler version of the problem, eventually reaching a base case that stops the recursion.",
        'expert': "Self-referential function definition requiring base case and recursive reduction. Stack-based execution with O(depth) space complexity."
    },

    # Dynamic Programming
    'dynamic_programming': {
        'beginner': "It's like remembering your homework answers. Instead of recalculating the same problem 100 times, you write down the answer the first time and reuse it.",
        'intermediate': "Optimization technique storing intermediate results to avoid recalculation. Solves overlapping subproblems efficiently.",
        'expert': "Memoization or tabulation approach for optimizing recursive algorithms with polynomial time via overlapping subproblem structure."
    },

    # Graph
    'graph': {
        'beginner': "It's like a map of cities connected by roads. Some roads are one-way (directed), some are two-way (undirected). Algorithms find shortest routes, all connected cities, etc.",
        'intermediate': "Abstract structure of nodes (vertices) connected by edges representing relationships, used for modeling networks and connectivity.",
        'expert': "Mathematical structure G = (V, E) with various representations (adjacency matrix, adjacency list) and algorithms (DFS, BFS, Dijkstra, Floyd-Warshall)."
    },

    # Cache/Caching
    'cache': {
        'beginner': "It's like keeping your most-used tools on your desk instead of in a storage room. Quick access to frequently used items speeds things up.",
        'intermediate': "Faster storage (memory) keeping frequently accessed data closer to processor, reducing access latency.",
        'expert': "Hierarchical memory system (L1/L2/L3 cache) with LRU eviction policy and coherence protocols for multi-core systems."
    },

    # API
    'api': {
        'beginner': "It's like a restaurant menu. Customers don't cook the food; they order from a menu of options. The kitchen handles the work behind the scenes.",
        'intermediate': "Interface for communication between software systems, specifying requests (endpoints), expected responses (contracts).",
        'expert': "RESTful or GraphQL architecture with stateless communication, idempotent operations, and standard HTTP semantics."
    },

    # Optimization
    'optimization': {
        'beginner': "It's like finding the shortest route to work. You try different paths and pick the fastest one.",
        'intermediate': "Process of finding the best solution from possible alternatives, often using gradient descent or other search algorithms.",
        'expert': "Mathematical optimization (convex/non-convex) with objective functions, constraints, and algorithms (SGD, Adam, L-BFGS)."
    },

    # Algorithm
    'algorithm': {
        'beginner': "It's like a recipe. Step-by-step instructions for solving a problem. Different recipes produce the same dish at different speeds.",
        'intermediate': "Finite sequence of well-defined steps solving a computational problem with defined input/output.",
        'expert': "Formal procedure with complexity analysis (time/space) and correctness proof via induction or invariant preservation."
    },

    # Complexity
    'complexity': {
        'beginner': "It measures how many operations an algorithm needs. O(n) is faster than O(n²) for large datasets.",
        'intermediate': "Big-O analysis quantifying algorithm performance: O(1) constant, O(log n) logarithmic, O(n) linear, O(n²) quadratic, O(2^n) exponential.",
        'expert': "Asymptotic analysis (Big-O, Big-Theta, Big-Omega) with tight bounds and complexity classes (P, NP, NP-complete)."
    },

    # Overfitting
    'overfitting': {
        'beginner': "It's like a student memorizing answers for specific test questions, then failing because the test has different questions. The model memorizes instead of learning.",
        'intermediate': "Model fitting training data too perfectly, capturing noise instead of patterns, resulting in poor generalization to new data.",
        'expert': "Excessive model complexity relative to training data size, managed via regularization (L1/L2), early stopping, or cross-validation."
    },

    # Underfitting
    'underfitting': {
        'beginner': "It's like a student studying too little. They don't learn enough to answer even basic questions on the test.",
        'intermediate': "Model too simple to capture underlying patterns, resulting in poor performance on both training and test data.",
        'expert': "Insufficient model capacity or under-regularization, addressed via model complexity increase or feature engineering."
    },

    # Trade-off
    'trade_off': {
        'beginner': "It's like choosing between a fast car (costs more) and an economical car (slower). You can't have everything.",
        'intermediate': "Situation where improving one aspect requires compromising another. Common: accuracy vs speed, bias vs variance, complexity vs interpretability.",
        'expert': "Bias-variance tradeoff where bias (underfitting) and variance (overfitting) cannot be minimized simultaneously."
    },

    # Parameter
    'parameter': {
        'beginner': "It's like a knob on a machine. Adjust the knob (parameter) to change how the machine works.",
        'intermediate': "Configuration variable controlling algorithm behavior. Different values produce different results.",
        'expert': "Learned weights/coefficients in models (vs hyperparameters which are set before training)."
    },

    # Hyperparameter
    'hyperparameter': {
        'beginner': "It's like recipe settings you decide BEFORE cooking (like oven temperature), not during cooking.",
        'intermediate': "Configuration set before training, controlling the learning process. Examples: learning rate, batch size, regularization strength.",
        'expert': "Tuned via grid search, random search, or Bayesian optimization on validation set to optimize generalization."
    }
}


def get_analogy(concept: str, user_level: str = 'beginner') -> str:
    """Get analogy for a concept at specified user level"""
    if concept in ANALOGY_DATABASE:
        analogies = ANALOGY_DATABASE[concept]
        if user_level in analogies:
            return analogies[user_level]
        # Return beginner by default
        return analogies.get('beginner', f"Concept: {concept}")
    return None


def get_all_analogies_for_concept(concept: str) -> dict:
    """Get all difficulty levels for a concept"""
    if concept in ANALOGY_DATABASE:
        return ANALOGY_DATABASE[concept]
    return {}


def list_concepts() -> list:
    """List all concepts with analogies"""
    return list(ANALOGY_DATABASE.keys())


def has_concept(concept: str) -> bool:
    """Check if concept has analogies"""
    return concept in ANALOGY_DATABASE
