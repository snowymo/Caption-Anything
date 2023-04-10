from io import BytesIO
import string
import gradio as gr
import requests
from caas import CaptionAnything
import torch
import json
import sys
import argparse
from caas import parse_augment
import numpy as np
import PIL.ImageDraw as ImageDraw
from image_editing_utils import create_bubble_frame
import copy


title = """<h1 align="center">Caption-Anything</h1>"""
description = """Gradio demo for Caption Anything, image to dense captioning generation with various language styles. To use it, simply upload your image, or click one of the examples to load them.
<br> <strong>Code</strong>: GitHub repo: < a href=' ' target='_blank'></ a>
"""

examples = [
    ["test_img/img2.jpg", "[[1000, 700, 1]]"]
]

args = parse_augment()
args.device = 'cuda:2'
args.disable_gpt = True
args.enable_reduce_tokens = True
args.port=20325

model = CaptionAnything(args)
# model = None

def get_prompt(chat_input, click_state):    
    points = click_state[0]
    labels = click_state[1]
    inputs = json.loads(chat_input)
    for input in inputs:
        points.append(input[:2])
        labels.append(input[2])
    
    prompt = {
        "prompt_type":["click"],
        "input_point":points,
        "input_label":labels,
        "multimask_output":"True",
    }
    return prompt
    
def inference_seg_cap(image_input, chat_input, language, sentiment, factuality, length, state, click_state, evt:gr.SelectData):
    controls = {'length': length,
             'sentiment': sentiment,
             'factuality': factuality,
             'language': language}
    click_coordinate = "[[{}, {}, 1]]".format(str(evt.index[0]), str(evt.index[1])) 
    chat_input = click_coordinate
    prompt = get_prompt(chat_input, click_state)
    print('prompt: ', prompt, 'controls: ', controls)
    out = model.inference(image_input, prompt, controls)
    state = state + [(None, "Image point: {}, Input label: {}".format(prompt["input_point"], prompt["input_label"]))]
    for k, v in out['generated_captions'].items():
        state = state + [(f'{k}: {v}', None)]
    
    text = out['generated_captions']['raw_caption']
    # draw = ImageDraw.Draw(image_input)
    # draw.text((evt.index[0], evt.index[1]), text, textcolor=(0,0,255), text_size=120)
    image_input = create_bubble_frame(image_input, text, (evt.index[0], evt.index[1])) 
    return text, click_state, chat_input, image_input


def upload_callback(image_input, state):
    state = state + [('Image size: ' + str(image_input.size), None)]
    return state, image_input


with gr.Blocks(
    css='''
    #image_upload{min-height:400px}
    #image_upload [data-testid="image"], #image_upload [data-testid="image"] > div{min-height: 600px}
    '''
) as iface:
    state = gr.State([])
    click_state = gr.State([[],[]])
    origin_image = gr.State(None)

    gr.Markdown(title)
    gr.Markdown(description)

    with gr.Row():
        with gr.Column(scale=1.0):
            image_input = gr.Image(type="pil", interactive=True, elem_id="image_upload")

            language = gr.Radio(
                choices=["English", "Chinese", "French", "Spanish", "Arabic", "Portuguese","Cantonese"],
                value="English",
                label="Language",
                interactive=True,
            )
            sentiment = gr.Radio(
                choices=["Positive", "Negative"],
                value="Positive",
                label="Sentiment",
                interactive=True,
            )
            factuality = gr.Radio(
                choices=["Factual", "Imagination"],
                value="Factual",
                label="Factuality",
                interactive=True,
            )
            length = gr.Slider(
                minimum=5,
                maximum=100,
                value=10,
                step=1,
                interactive=True,
                label="Length",
            )

    with gr.Row(scale=1.5):
        with gr.Column():
            chat_input = gr.Textbox(lines=1, label="Chat Input")
    examples = gr.Examples(
        examples=examples,
        inputs=[image_input, chat_input],
    )

    image_input.upload(upload_callback,[image_input, state], [state, origin_image])

    # select coordinate
    image_input.select(inference_seg_cap, 
        inputs=[
        origin_image,
        chat_input,
        language,
        sentiment,
        factuality,
        length,
        state,
        click_state
        ],
    outputs=[state, click_state, chat_input, image_input],
    show_progress=False)
        
    image_input.change(
        lambda: ([], [[], []]),
        [],
        [state, click_state],
        queue=False,
    )

iface.queue(concurrency_count=1, api_open=False, max_size=10)
iface.launch(server_name="0.0.0.0", enable_queue=True, server_port=args.port, share=args.gradio_share)