from django.db import models

class Portfolio(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=10, default='📊')

    def stock_count(self):
        return self.stocks.count()
