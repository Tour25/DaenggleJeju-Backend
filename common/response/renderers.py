from http import HTTPStatus
from rest_framework.renderers import JSONRenderer

def _reason(code: int) -> str:
    try: return HTTPStatus(code).phrase
    except: return "OK" if 200 <= code < 300 else "Error"

class EnvelopedJSONRenderer(JSONRenderer):

    def render(self, data, accepted_media_type=None, renderer_context=None):
        rc = renderer_context or {}
        response = rc.get("response")
        request = rc.get("request")

        if not response or response.get("X-Skip-Envelope") == "1":
            return super().render(data, accepted_media_type, rc)

        status_code = getattr(response, "status_code", 200)
        if 200 <= status_code < 300:
            if isinstance(data, dict) and {"code","message","result"} <= data.keys():
                return super().render(data, accepted_media_type, rc)
            message = getattr(request, "_resp_message", None) if request else None
            data = {"code": str(status_code), "message": message or _reason(status_code), "result": data}
        return super().render(data, accepted_media_type, rc)
