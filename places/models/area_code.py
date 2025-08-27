from django.db import models

class AreaCode(models.Model):
    code=models.CharField(max_length=10, primary_key=True) #지역 코드
    name=models.CharField(max_length=100) #지역명
    #상위 지역
    parent=models.ForeignKey("self",
                             null=True, blank=True,
                             on_delete=models.CASCADE,
                             related_name="children")

    class Meta:
        indexes=[
            models.Index(fields=["parent"]),
        ]


    def __str__(self):
        if not self.parent:
            return f"{self.name} ({self.code})"
        return f"{self.parent.name} > {self.name} ({self.code})"
