from modeltranslation.translator import translator, TranslationOptions
from .models import Category, Restaurant, Product

class CategoryTranslationOptions(TranslationOptions):
    fields = ('name', 'description')

class RestaurantTranslationOptions(TranslationOptions):
    fields = ('name', 'description')

class ProductTranslationOptions(TranslationOptions):
    fields = ('name', 'description')

translator.register(Category, CategoryTranslationOptions)
translator.register(Restaurant, RestaurantTranslationOptions)
translator.register(Product, ProductTranslationOptions)
