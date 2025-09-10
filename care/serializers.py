from rest_framework import serializers
from .content import TOPICS, get_script


TOPIC_IDS = [t["id"] for t in TOPICS]


def _build_chip_doc():
    lines = []
    for t in TOPICS:
        chips = " | ".join(t["chips"])
        lines.append(f"- {t['id']}: {chips}")
    return "\n".join(lines)

CHIP_DOC = _build_chip_doc()


class ScriptQuerySerializer(serializers.Serializer):
    topic = serializers.ChoiceField(choices=TOPIC_IDS, help_text="토픽 ID")
    option = serializers.CharField(
        max_length=100,
        help_text=f"칩(한글 그대로)\n{CHIP_DOC}",
    )

    def validate(self, attrs):

        try:
            get_script(attrs["topic"], attrs["option"])
        except KeyError:
            raise serializers.ValidationError("unknown topic/option")
        return attrs

class MessageSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["script"])
    markdown = serializers.CharField()

class MessageResponseSerializer(serializers.Serializer):
    message = MessageSerializer()

class TopicItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    chips = serializers.ListField(child=serializers.CharField())

class AskBodySerializer(serializers.Serializer):
    question = serializers.CharField(max_length=2000, help_text="사용자 자유 질문")

class AnswerMessageSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["answer"])
    markdown = serializers.CharField()

class AskResponseSerializer(serializers.Serializer):
    message = AnswerMessageSerializer()