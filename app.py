import gradio as gr
from DB_Query import Q
import pandas as pd

q = None
company = False  

def upload_csv(file, company_flag):
    global q
    df = pd.read_csv(file.name)
    if df.empty:
        return "Dataframe upload has failed"
    
    q = Q(df, model='gpt-4o-mini', company=company_flag) 
    return df.head()  # Show a preview of the uploaded data

def set_company_flag(checked):
    global company
    company = checked
    return f"Company flag set to: {company}"

def chat_with_diallo(user_input, history):
    global q
    if q is None:
        return history + [(user_input, "Please upload a CSV file first.")]
    
    text, img = q.ask_diallo(user_input)
    
    if not text and not img:
        reply = "I was unable to answer that question"
    elif img:
        reply = f"{text}<br><img src='data:image/png;base64,{img}'>" if text else f"<img src='data:image/png;base64,{img}'>"
    else:
        reply = text
    
    messages = history + [{"role": "user", "content": user_input},
                          {"role": "assistant", "content": reply}]
    return messages
    
with gr.Blocks() as win:
    gr.Markdown("# Chatbot with CSV Upload")
    
    company_checkbox = gr.Checkbox(label="Company", value=False, info="Tick this if you want to enable company mode.")
    company_status = gr.Textbox(label="Company Flag Status", interactive=False)
    
    with gr.Row():
        csv_upload = gr.File(label="Upload your CSV file")
        upload_button = gr.Button("Upload")
    
    upload_status = gr.Textbox(label="Upload Status", interactive=False)
    
    chatbot = gr.Chatbot(label="Chat with Amad Diallo",type="messages")
    user_input = gr.Textbox(label="Your Message", placeholder="Ask me something about the CSV...")
    send_button = gr.Button("Send")
        
    company_checkbox.change(
        set_company_flag,
        inputs=company_checkbox,
        outputs=company_status,
    )
    
    upload_button.click(
        upload_csv,
        inputs=[csv_upload, company_checkbox], 
        outputs=upload_status,
    )
    
    send_button.click(
        chat_with_diallo,
        inputs=[user_input, chatbot],
        outputs=[chatbot],
    )

win.launch()