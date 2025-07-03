import streamlit as st
import random
import sympy as sp

# Function to generate a random math problem
def generate_problem():
    problem_types = ['quadratic_equation', 'trigonometry', 'coordinate_geometry', 'sequence', 'vectors']
    problem_type = random.choice(problem_types)
    
    if problem_type == 'quadratic_equation':
        # Quadratic equation: ax^2 + bx + c = 0, find roots
        a = random.randint(1, 5)
        b = random.randint(-10, 10)
        c = random.randint(-10, 10)
        question = f"Solve the quadratic equation: {a}x² + {b}x + {c} = 0"
        
        # Calculate correct roots using SymPy
        x = sp.Symbol('x')
        equation = a*x**2 + b*x + c
        roots = sp.solve(equation, x)
        if len(roots) == 2:
            correct_answer = f"({roots[0]}, {roots[1]})"
        else:
            correct_answer = f"({roots[0]})"
        
        # Generate distractors
        distractors = []
        for _ in range(3):
            fake_root1 = roots[0] + random.randint(-2, 2)
            fake_root2 = roots[1] + random.randint(-2, 2) if len(roots) == 2 else fake_root1
            distractors.append(f"({fake_root1}, {fake_root2})")
        
        # Ensure distractors are unique and not correct
        distractors = list(set(distractors) - {correct_answer})
        while len(distractors) < 3:
            fake_root1 = roots[0] + random.randint(-3, 3)
            fake_root2 = roots[1] + random.randint(-3, 3) if len(roots) == 2 else fake_root1
            new_option = f"({fake_root1}, {fake_root2})"
            if new_option != correct_answer and new_option not in distractors:
                distractors.append(new_option)
        
        options = [correct_answer] + distractors[:3]
        random.shuffle(options)
        
        # Explanation
        discriminant = b**2 - 4*a*c
        explanation = f"Use the quadratic formula x = [-b ± √(b² - 4ac)]/(2a). Here, a = {a}, b = {b}, c = {c}. Discriminant = {b}^2 - 4*{a}*{c} = {discriminant}. Roots are {roots}."
        
        return question, options, correct_answer, explanation
    
    elif problem_type == 'trigonometry':
        # Trigonometric identity: sin^2(x) + cos^2(x) = 1 related
        angle = random.randint(30, 60)  # Common angles for simplicity
        question = f"If sin({angle}°) = {sp.sin(sp.rad(angle)).evalf():.3f}, find cos({angle}°)."
        
        # Correct answer
        correct_answer = f"{sp.cos(sp.rad(angle)).evalf():.3f}"
        
        # Generate distractors
        distractors = []
        for _ in range(3):
            fake_cos = float(correct_answer) + random.uniform(-0.2, 0.2)
            fake_cos = round(min(max(fake_cos, -1), 1), 3)  # Keep within [-1, 1]
            distractors.append(f"{fake_cos:.3f}")
        
        # Ensure distractors are unique and not correct
        distractors = list(set(distractors) - {correct_answer})
        while len(distractors) < 3:
            fake_cos = float(correct_answer) + random.uniform(-0.3, 0.3)
            fake_cos = round(min(max(fake_cos, -1), 1), 3)
            new_option = f"{fake_cos:.3f}"
            if new_option != correct_answer and new_option not in distractors:
                distractors.append(new_option)
        
        options = [correct_answer] + distractors[:3]
        random.shuffle(options)
        
        # Explanation
        explanation = f"Use the identity sin²(θ) + cos²(θ) = 1. Given sin({angle}°) = {sp.sin(sp.rad(angle)).evalf():.3f}, compute cos²({angle}°) = 1 - sin²({angle}°) = 1 - ({sp.sin(sp.rad(angle)).evalf():.3f})². Then, cos({angle}°) = ±√(cos²({angle}°)). Since {angle}° is in Q1, cos({angle}°) is positive."
        
        return question, options, correct_answer, explanation
    
    elif problem_type == 'coordinate_geometry':
        # Distance between two points
        x1, y1 = random.randint(-5, 5), random.randint(-5, 5)
        x2, y2 = random.randint(-5, 5), random.randint(-5, 5)
        question = f"Find the distance between points ({x1}, {y1}) and ({x2}, {y2})."
        
        # Correct answer
        distance = sp.sqrt((x2 - x1)**2 + (y2 - y1)**2).evalf()
        correct_answer = f"{distance:.2f}"
        
        # Generate distractors
        distractors = []
        for _ in range(3):
            fake_distance = float(distance) + random.uniform(-2, 2)
            fake_distance = round(max(fake_distance, 0), 2)
            distractors.append(f"{fake_distance:.2f}")
        
        # Ensure distractors are unique and not correct
        distractors = list(set(distractors) - {correct_answer})
        while len(distractors) < 3:
            fake_distance = float(distance) + random.uniform(-3, 3)
            fake_distance = round(max(fake_distance, 0), 2)
            new_option = f"{fake_distance:.2f}"
            if new_option != correct_answer and new_option not in distractors:
                distractors.append(new_option)
        
        options = [correct_answer] + distractors[:3]
        random.shuffle(options)
        
        # Explanation
        explanation = f"Use the distance formula: √((x₂ - x₁)² + (y₂ - y₁)²). For points ({x1}, {y1}) and ({x2}, {y2}), distance = √(({x2} - {x1})² + ({y2} - {y1})²) = √({(x2-x1)**2} + {(y2-y1)**2}) = {distance:.2f}."
        
        return question, options, correct_answer, explanation
    
    elif problem_type == 'sequence':
        # Arithmetic progression: Find nth term
        a = random.randint(1, 10)  # First term
        d = random.randint(1, 5)   # Common difference
        n = random.randint(5, 10)  # Term number
        question = f"Find the {n}th term of the arithmetic sequence with first term {a} and common difference {d}."
        
        # Correct answer
        nth_term = a + (n-1)*d
        correct_answer = f"{nth_term}"
        
        # Generate distractors
        distractors = []
        for _ in range(3):
            fake_term = nth_term + random.randint(-10, 10)
            distractors.append(f"{fake_term}")
        
        # Ensure distractors are unique and not correct
        distractors = list(set(distractors) - {correct_answer})
        while len(distractors) < 3:
            fake_term = nth_term + random.randint(-15, 15)
            new_option = f"{fake_term}"
            if new_option != correct_answer and new_option not in distractors:
                distractors.append(new_option)
        
        options = [correct_answer] + distractors[:3]
        random.shuffle(options)
        
        # Explanation
        explanation = f"The nth term of an arithmetic sequence is given by aₙ = a + (n-1)d. Here, a = {a}, d = {d}, n = {n}. So, aₙ = {a} + ({n}-1)*{d} = {a} + {(n-1)*d} = {nth_term}."
        
        return question, options, correct_answer, explanation
    
    elif problem_type == 'vectors':
        # Vector problem: Magnitude or dot product
        vector_problem_type = random.choice(['magnitude', 'dot_product'])
        
        if vector_problem_type == 'magnitude':
            # Find magnitude of a 2D vector
            a1, a2 = random.randint(-5, 5), random.randint(-5, 5)
            question = f"Find the magnitude of the vector ({a1}, {a2})."
            
            # Correct answer
            magnitude = sp.sqrt(a1**2 + a2**2).evalf()
            correct_answer = f"{magnitude:.2f}"
            
            # Generate distractors
            distractors = []
            for _ in range(3):
                fake_magnitude = float(magnitude) + random.uniform(-2, 2)
                fake_magnitude = round(max(fake_magnitude, 0), 2)
                distractors.append(f"{fake_magnitude:.2f}")
            
            # Ensure distractors are unique and not correct
            distractors = list(set(distractors) - {correct_answer})
            while len(distractors) < 3:
                fake_magnitude = float(magnitude) + random.uniform(-3, 3)
                fake_magnitude = round(max(fake_magnitude, 0), 2)
                new_option = f"{fake_magnitude:.2f}"
                if new_option != correct_answer and new_option not in distractors:
                    distractors.append(new_option)
            
            options = [correct_answer] + distractors[:3]
            random.shuffle(options)
            
            # Explanation
            explanation = f"The magnitude of a vector (a, b) is given by √(a² + b²). For vector ({a1}, {a2}), magnitude = √({a1}² + {a2}²) = √({a1**2} + {a2**2}) = {magnitude:.2f}."
            
            return question, options, correct_answer, explanation
        
        elif vector_problem_type == 'dot_product':
            # Find dot product of two 2D vectors
            a1, a2 = random.randint(-5, 5), random.randint(-5, 5)
            b1, b2 = random.randint(-5, 5), random.randint(-5, 5)
            question = f"Find the dot product of vectors ({a1}, {a2}) and ({b1}, {b2})."
            
            # Correct answer
            dot_product = a1*b1 + a2*b2
            correct_answer = f"{dot_product}"
            
            # Generate distractors
            distractors = []
            for _ in range(3):
                fake_dot = dot_product + random.randint(-10, 10)
                distractors.append(f"{fake_dot}")
            
            # Ensure distractors are unique and not correct
            distractors = list(set(distractors) - {correct_answer})
            while len(distractors) < 3:
                fake_dot = dot_product + random.randint(-15, 15)
                new_option = f"{fake_dot}"
                if new_option != correct_answer and new_option not in distractors:
                    distractors.append(new_option)
            
            options = [correct_answer] + distractors[:3]
            random.shuffle(options)
            
            # Explanation
            explanation = f"The dot product of vectors (a₁, a₂) and (b₁, b₂) is a₁b₁ + a₂b₂. For vectors ({a1}, {a2}) and ({b1}, {b2}), dot product = {a1}*{b1} + {a2}*{b2} = {a1*b1} + {a2*b2} = {dot_product}."
            
            return question, options, correct_answer, explanation

# Streamlit app
st.title("IIT JEE Math Practice Quiz (11th Grade)")
st.write("Practice math problems for JEE Main preparation!")

# Initialize session state
if 'problem' not in st.session_state:
    st.session_state.problem = None
    st.session_state.options = None
    st.session_state.correct_answer = None
    st.session_state.explanation = None
    st.session_state.submitted = False
    st.session_state.user_answer = None

# Generate new problem button
if st.button("Generate New Problem"):
    st.session_state.problem, st.session_state.options, st.session_state.correct_answer, st.session_state.explanation = generate_problem()
    st.session_state.submitted = False
    st.session_state.user_answer = None

# Display problem and options
if st.session_state.problem:
    st.write("**Problem:**")
    st.write(st.session_state.problem)
    st.write("**Options:**")
    
    # Radio buttons for MCQ
    user_answer = st.radio("Select your answer:", st.session_state.options, key="mcq")
    
    # Submit button
    if st.button("Submit Answer"):
        st.session_state.submitted = True
        st.session_state.user_answer = user_answer
    
    # Display result and explanation
    if st.session_state.submitted:
        if st.session_state.user_answer == st.session_state.correct_answer:
            st.success("Correct!")
        else:
            st.error(f"Incorrect. The correct answer is: {st.session_state.correct_answer}")
        st.write("**Explanation:**")
        st.write(st.session_state.explanation)
else:
    st.write("Click 'Generate New Problem' to start!")
