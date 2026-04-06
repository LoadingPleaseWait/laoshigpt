#!/usr/bin/env python
# coding: utf-8

import asyncio

async def CallLLM():
    # In[ ]:


    import getpass
    import os

    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")

    from agents.realtime import RealtimeAgent, RealtimeRunner
    agent = RealtimeAgent(name="Laoshi", instructions="You are an expert Chinese language tutor with over 10 years of experience. \
        Use the following communication style: encouraging, patient, culturally sensitive and systematically progressive. \
        Gently correct mistakes (including pronounciation mistakes) in real time. \
        Regularly highlight student achievements and improvements to maintain motivation. \
        You are tutoring a native US English speaker. \
        Format your responses so that they are concise, teaching a little bit at a time \
        When speaking Chinese, never use vocabulary above the pre-2021 HSK-3 level under any circumstances.")

    runner = RealtimeRunner(
        starting_agent=agent,
        config={
            "model_settings": {
                "model_name": "gpt-realtime",
                "voice": "alloy",
                "modalities": ["text", "audio"],
            }
        }
    )


    # In[4]:


    session = await runner.run()

    # Send a text message to start the conversation
    await session.send_message("Hello! How are you today?")

    # The agent will stream back audio in real-time (not shown in this example)
    # Listen for events from the session
    for event in session:
        if event.type == "response.audio_transcript.done":
            print(f"Assistant: {event.transcript}")
        elif event.type == "conversation.item.input_audio_transcription.completed":
            print(f"User: {event.transcript}")

    while True:
      user_input = input("You>:")
      result = await Runner.run(agent, user_input)
      print("Teacher>:", end="")
      print(result.final_output)


    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import START, MessagesState, StateGraph

    # Define a new graph
    workflow = StateGraph(state_schema=MessagesState)

    def call_model(state: MessagesState):
        prompt = chat_prompt_template.invoke(state["messages"])
        response = model.invoke(prompt)
        return {"messages": response}

    # Define the (single) node in the graph
    workflow.add_edge(START, "model")
    workflow.add_node("model", call_model)

    #Adding Memory
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)


    # In[ ]:


    from langchain_core.messages import HumanMessage
    from gtts import gTTS
    from io import BytesIO
    from pydub import AudioSegment
    from pydub.playback import play

    config = {"configurable": {"thread_id": "CM"}}
    while True:
      user_input = input("You>:")
      input_messages = [HumanMessage(user_input)]
      output = app.invoke({"messages": input_messages}, config)
      last_message = output["messages"][-1]
      print("Teacher>:", end="")
      last_message.pretty_print()
      # Use gTTS and pygame to say the AI message with Taiwanese voice
      mp3_file_like = BytesIO()
      tts = gTTS(text=last_message.text(), lang='zh-TW', slow=False)
      tts.write_to_fp(mp3_file_like)
      mp3_file_like.seek(0)
      # Convert the file-like object to an AudioSegment
      audio = AudioSegment.from_mp3(BytesIO(mp3_file_like.read()))
      # Play the sound
      play(audio)
      mp3_file_like.close()


asyncio.run(callLLM())
