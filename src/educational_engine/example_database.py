# educational_engine/example_database.py
"""
Example Database - Pre-Built Domain-Specific Examples

Hardcoded real-world examples for common ML/CS concepts.
NO LLM generation - all examples pre-built and organized by domain.

NO LLM CALLS - Examples are loaded once at startup.
"""

EXAMPLE_DATABASE = {
    # Decision Tree examples
    'decision_tree': {
        'hiring_process': {
            'context': 'Making hiring decisions for software engineer positions',
            'example': '''
            Question 1: "Does candidate have CS degree or 5+ years experience?"
              YES → Continue to next question
              NO → Reject

            Question 2: "Has candidate worked with our tech stack (Python, React)?"
              YES → Continue to interview
              NO → Reject (unless exceptional)

            Question 3: "Did they pass technical interview?"
              YES → Offer job
              NO → Reject

            Result: Each path leads to a decision (Hire or Reject)
            ''',
            'key_insight': 'Each branch asks ONE yes/no question, narrowing down to a decision'
        },
        'disease_diagnosis': {
            'context': 'Diagnosing patient health conditions in medical triage',
            'example': '''
            Question 1: "Does patient have fever?"
              YES → Check symptoms
              NO → Likely not infection-based

            Question 2: "Is cough present?"
              YES → Possible respiratory infection
              NO → Check other symptoms

            Result: Path through tree narrows possible diagnoses
            ''',
            'key_insight': 'Each question partitions patients into groups'
        },
        'email_classification': {
            'context': 'Classifying emails as spam or not spam',
            'example': '''
            Question 1: "Contains suspicious sender domain?"
              YES → Likely spam
              NO → Continue checking

            Question 2: "Contains request for money/passwords?"
              YES → Spam
              NO → Likely legitimate

            Result: Emails classified into spam/not-spam buckets
            ''',
            'key_insight': 'Simple yes/no questions create binary splits'
        }
    },

    # Regression examples
    'regression': {
        'house_price': {
            'context': 'Predicting house price based on square footage',
            'example': '''
            Historical data:
            - 1000 sq ft house → $150,000
            - 2000 sq ft house → $300,000
            - 3000 sq ft house → $450,000

            Pattern: Price = 150,000 + (150 × square_feet)

            Prediction: 2500 sq ft house → 150,000 + (150 × 2500) = $525,000
            ''',
            'key_insight': 'Find line that fits historical data, then predict new values'
        },
        'sales_forecasting': {
            'context': 'Predicting monthly revenue from advertising spend',
            'example': '''
            Historical months:
            - $1000 ad spend → $50,000 revenue
            - $2000 ad spend → $85,000 revenue
            - $3000 ad spend → $120,000 revenue

            Relationship: Revenue ≈ 10,000 + (35 × ad_spend)

            Prediction: If spend $4000 → ~$150,000 revenue
            ''',
            'key_insight': 'Linear relationship allows prediction of new outcomes'
        }
    },

    # Clustering examples
    'clustering': {
        'customer_segmentation': {
            'context': 'Grouping customers by purchase behavior (no predefined labels)',
            'example': '''
            Customer data: (monthly_spend, purchase_frequency, product_category)

            Algorithm finds 3 natural groups:

            Cluster 1: HIGH spend ($5000+), HIGH frequency (20+ purchases/month)
              → "Premium customers" (not labeled, discovered)

            Cluster 2: MEDIUM spend ($500-$1000), MEDIUM frequency (5-10 purchases)
              → "Regular customers" (not labeled, discovered)

            Cluster 3: LOW spend (<$100), LOW frequency (1-2 purchases/month)
              → "Occasional customers" (not labeled, discovered)

            Benefit: No need to pre-define customer segments
            ''',
            'key_insight': 'Algorithm finds natural groupings without predefined categories'
        },
        'animal_classification': {
            'context': 'Grouping animals by features (DNA, physical traits)',
            'example': '''
            Animal features: (legs, fur, diet, habitat)

            Groups discovered:
            - Carnivores: cats, dogs, bears (similar hunting behavior)
            - Herbivores: cows, sheep, deer (similar eating patterns)
            - Omnivores: bears, humans, pigs (mixed diet)

            Benefit: Algorithm discovers relationships without telling it labels
            ''',
            'key_insight': 'Similar items group together naturally'
        }
    },

    # Neural Network examples
    'neural_network': {
        'handwritten_digit': {
            'context': 'Recognizing handwritten numbers 0-9 from 28×28 pixel images',
            'example': '''
            Layer 1 (Simple features): Detects edges and lines in pixels
            Layer 2 (Complex features): Combines edges into curves and shapes
            Layer 3 (Patterns): Recognizes digit patterns (circles, lines, etc.)
            Layer 4 (Decision): "This pattern looks like number 7"

            Training: Show 60,000 examples of handwritten digits
            Network learns: "When I see THIS pattern, output 7"

            Result: 99% accuracy on new handwritten digits
            ''',
            'key_insight': 'Network learns features automatically through layers'
        },
        'image_recognition': {
            'context': 'Identifying objects in photos (cat, dog, car, etc.)',
            'example': '''
            Layer 1: Detects colors, textures
            Layer 2: Detects shapes (circles for face, triangles for ears)
            Layer 3: Combines shapes ("two triangles on circle" = cat face)
            Layer 4: Final decision: "This is a cat"

            Same principle as digit recognition but more complex patterns
            ''',
            'key_insight': 'Progressive feature learning through network depth'
        }
    },

    # Algorithm examples
    'quicksort': {
        'sorting_cards': {
            'context': 'Sorting a deck of cards from lowest to highest',
            'example': '''
            Initial deck: [5, 2, 8, 1, 9]

            Step 1: Pick pivot = 5
                Left (smaller): [2, 1]
                Pivot: [5]
                Right (larger): [8, 9]

            Step 2: Recursively sort left [2, 1] → [1, 2]
            Step 3: Recursively sort right [8, 9] → [8, 9]

            Result: [1, 2] + [5] + [8, 9] = [1, 2, 5, 8, 9]
            ''',
            'key_insight': 'Divide problem into smaller subproblems, solve, combine'
        }
    },

    # Recursion examples
    'recursion': {
        'factorial': {
            'context': 'Computing 5! = 5 × 4 × 3 × 2 × 1',
            'example': '''
            factorial(5) = 5 × factorial(4)
            factorial(4) = 4 × factorial(3)
            factorial(3) = 3 × factorial(2)
            factorial(2) = 2 × factorial(1)
            factorial(1) = 1  ← BASE CASE (stops recursion)

            Working backwards:
            factorial(2) = 2 × 1 = 2
            factorial(3) = 3 × 2 = 6
            factorial(4) = 4 × 6 = 24
            factorial(5) = 5 × 24 = 120
            ''',
            'key_insight': 'Function calls itself with simpler input until base case'
        },
        'tree_traversal': {
            'context': 'Visiting every node in a tree structure',
            'example': '''
                    Root
                   /    \\
                  L      R
                 / \\
                LL  LR

            Recursion:
            visit(Root):
              visit(Left subtree)
                visit(LL)
                visit(LR)
              visit(Right subtree)

            Result: All nodes visited: Root, L, LL, LR, R
            ''',
            'key_insight': 'Recursive structure for recursive problems'
        }
    },

    # Dynamic Programming examples
    'dynamic_programming': {
        'fibonacci': {
            'context': 'Computing Fibonacci sequence: 1, 1, 2, 3, 5, 8, ...',
            'example': '''
            Without DP (slow):
            fib(5) → fib(4) + fib(3)
            fib(4) → fib(3) + fib(2)
            fib(3) calculated 3 TIMES (wasted work)

            With DP (fast):
            fib(1) = 1
            fib(2) = 1
            fib(3) = fib(2) + fib(1) = 2
            fib(4) = fib(3) + fib(2) = 3 (reuse cached fib(3))
            fib(5) = fib(4) + fib(3) = 5 (reuse cached results)

            Benefit: Each value calculated ONCE, then reused
            ''',
            'key_insight': 'Cache results to avoid recalculation'
        },
        'longest_common_substring': {
            'context': 'Finding similar parts between two strings',
            'example': '''
            String 1: "ABCDGH"
            String 2: "AEDFHR"

            Build table of matches:
              "" A E D F H R
            "" 0  0 0 0 0 0 0
            A  0  1 0 0 0 0 0
            B  0  1 0 0 0 0 0
            C  0  1 0 0 0 0 0
            D  0  1 0 1 0 0 0
            G  0  1 0 1 0 0 0
            H  0  1 0 1 0 1 0

            Result: Common substrings found via cached comparisons
            ''',
            'key_insight': 'Build up solution from smaller subproblems'
        }
    }
}


def get_example(concept: str, domain: str = None) -> dict:
    """Get example for a concept"""
    if concept in EXAMPLE_DATABASE:
        if domain is None:
            # Return first example
            examples = EXAMPLE_DATABASE[concept]
            first_key = list(examples.keys())[0]
            return examples[first_key]
        elif domain in EXAMPLE_DATABASE[concept]:
            return EXAMPLE_DATABASE[concept][domain]
    return None


def list_examples_for_concept(concept: str) -> list:
    """List all available example domains for a concept"""
    if concept in EXAMPLE_DATABASE:
        return list(EXAMPLE_DATABASE[concept].keys())
    return []


def list_all_concepts() -> list:
    """List all available concepts with examples"""
    return list(EXAMPLE_DATABASE.keys())
