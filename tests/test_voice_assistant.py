from voice import VoiceAssistant


def test_wake_word():
    doug = VoiceAssistant()
    assert doug.handle("hey doug hello") == "I heard: hello"


def test_time_tool():
    doug = VoiceAssistant()
    result = doug.handle("hey doug what time is it")
    assert result.startswith("It is ")


def test_custom_brain():
    doug = VoiceAssistant(responder=lambda prompt: "brain:" + prompt)
    assert doug.handle("hey doug remember this") == "brain:remember this"


def test_empty_wake_word():
    doug = VoiceAssistant()
    assert doug.handle("hey doug") == "I'm listening."
