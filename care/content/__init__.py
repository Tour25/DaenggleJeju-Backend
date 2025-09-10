from . import move_stress
from . import food_check
from . import parasite_prevent
from . import dehydration_fatigue

TOPICS = [
    {"id": move_stress.TOPIC_ID,        "title": move_stress.TITLE,        "chips": move_stress.CHIPS},
    {"id": food_check.TOPIC_ID,         "title": food_check.TITLE,         "chips": food_check.CHIPS},
    {"id": parasite_prevent.TOPIC_ID,   "title": parasite_prevent.TITLE,   "chips": parasite_prevent.CHIPS},
    {"id": dehydration_fatigue.TOPIC_ID,"title": dehydration_fatigue.TITLE,"chips": dehydration_fatigue.CHIPS},
]

def get_script(topic_id: str, option_kor: str) -> str:
    if topic_id == move_stress.TOPIC_ID:
        return move_stress.get_markdown(option_kor)
    if topic_id == food_check.TOPIC_ID:
        return food_check.get_markdown(option_kor)
    if topic_id == parasite_prevent.TOPIC_ID:
        return parasite_prevent.get_markdown(option_kor)
    if topic_id == dehydration_fatigue.TOPIC_ID:
        return dehydration_fatigue.get_markdown(option_kor)
    raise KeyError("unknown topic")
