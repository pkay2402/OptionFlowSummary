import streamlit as st
import random

# Set up the page configuration
st.set_page_config(page_title="Math Fun!", page_icon=":tada:", layout="wide")

# Initialize session state for score, name, and current problem
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'name' not in st.session_state:
    st.session_state.name = ""
if 'current_problem' not in st.session_state:
    st.session_state.current_problem = None

# Function to generate a math problem
def generate_problem():
    operation = random.choice(['+', '-'])
    if operation == '+':
        a, b = random.randint(1, 9), random.randint(1, 9)
    else:
        a = random.randint(1, 9)
        b = random.randint(1, a)  # Ensure subtraction is always positive
    return f"{a} {operation} {b}"

# Function to check the answer
def check_answer(problem, answer):
    try:
        return eval(problem) == int(answer)
    except:
        return False

# Name input section
if not st.session_state.name:
    st.title("Welcome to Math Fun!")
    name = st.text_input("Please enter your name:")
    if st.button("Start"):
        if name:
            st.session_state.name = name
            st.session_state.current_problem = generate_problem()
            st.rerun()
        else:
            st.warning("Please enter your name to start!")
else:
    # Title and basic setup after name is entered
    st.title(f"Math Fun with {st.session_state.name}!")
    st.write("Let's practice some math!")

    # Display the current problem or generate a new one if it's None
    if not st.session_state.current_problem:
        st.session_state.current_problem = generate_problem()

    st.header(f"What is {st.session_state.current_problem}?")

    # User input for answer with a unique key
    answer = st.text_input("Your answer:", key="answer_input")

    # Column layout for buttons
    col1, col2 = st.columns(2)

    # Check answer when button is clicked
    if col1.button("Check Answer"):
        if check_answer(st.session_state.current_problem, answer):
            st.session_state.score += 1
            st.success(f"Correct! Great job, {st.session_state.name}!")
            st.balloons()  # Fun effect for correct answers
        else:
            st.error("Oops! Try again.")
            st.write(f"Remember, {st.session_state.name}, you can do this!")
        
        # Clear the text input by setting it to an empty string
        answer = ""
        
    # Generate next problem when button is clicked
    if col2.button("Next Problem"):
        st.session_state.current_problem = generate_problem()
        # Clear the answer input
        answer = ""
        st.rerun()

    # Display the score
    st.write(f"Your Score, {st.session_state.name}: **{st.session_state.score}**")

    # Encouragement
    if st.session_state.score > 0:
        st.write(f"You're doing amazing, {st.session_state.name}! Keep going!")
    else:
        st.write(f"Every try is a step closer to being a math wizard, {st.session_state.name}!")

    # Footer with fun message
    st.write("Powered by Numbers and Magic! :sparkles:")

    # Reset Button
    if st.button("Reset Game"):
        st.session_state.score = 0
        st.session_state.name = ""
        st.session_state.current_problem = None
        st.rerun()
