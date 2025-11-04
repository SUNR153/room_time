from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

User =  get_user_model()

class RegisterSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        field = ['id','email','password','username']
        extra_kwards = {'password' : {'write_only' : True}}
    def create(self,validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return User.objects.create(**validated_data)
    


    