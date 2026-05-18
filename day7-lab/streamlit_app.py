import streamlit as st

# Counter
if "counter" not in st.session_state:
	st.session_state["counter"] = 0

# Side bar
st.sidebar.title("Profile Page")
name = st.sidebar.text_input("Name")

# Main content
st.title("Resume App")
if name != "":
	display_string = (f"Hello {name} 👋")
else:
	display_string = ("Hello 👋")
st.text(display_string)

# Accept files
upload = st.file_uploader("Upload resume", type=["pdf", "txt"])
if upload:
	st.success(f"Successfully uploaded: {upload.name}")	
	st.session_state["counter"] += 1
	st.text(f"File Upload Counter: {st.session_state["counter"]}")