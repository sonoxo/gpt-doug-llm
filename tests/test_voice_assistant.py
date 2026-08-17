from voice import VoiceAssistant


def test_wake_word():
    doug = VoiceAssistant()
    assert doug.handle("hey doug what time is it") == "I heard: what time is it"


def test_custom_brain():
    doug = VoiceAssistant(responder=lambda prompt: "brain:" + prompt)
    assert doug.handle("hey doug remember this") == "brain:remember this"


def test_empty_wake_word():
    doug = VoiceAssistant()
    assert doug.handle("hey doug") == "I'm listening."
