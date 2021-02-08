from .models import Tag, Search
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from . import serializers

import pandas as pd
import requests
import json
import itertools
import re
from datetime import datetime as dt

def get_credentials():
    credentials = {}
    credentials['graph_domain'] = 'https://graph.facebook.com/'
    credentials['graph_version'] = 'v9.0'
    credentials['endpoint_base'] = credentials['graph_domain'] + credentials['graph_version'] + '/'
    return credentials


# Instagram Graph API�R�[��
def call_api(url, endpoint_params):
    data = requests.get(url, endpoint_params)
    response = {}
    response['json_data'] = json.loads(data.content)
    return response


# �n�b�V���^�OID�擾
def get_hashtag_id(params):
    endpoint_params = {}
    endpoint_params['user_id'] = params['instagram_account_id']
    endpoint_params['q'] = params['tagname']
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + 'ig_hashtag_search'
    return call_api(url, endpoint_params)


# �g�b�v���f�B�A�擾
def get_hashtag_media(params):
    endpoint_params = {}
    endpoint_params['user_id'] = params['instagram_account_id']
    endpoint_params['fields'] = 'caption'
    # endpoint_params['limit'] = 50
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['hashtag_id'] + '/top_media'
    return call_api(url, endpoint_params)


# ���[�U�[�A�J�E���g���擾
def get_account_info(params):
    endpoint_params = {}
    # ���[�U���A�v���t�B�[���摜�A�t�H�����[���A�t�H���[���A���e���A���f�B�A���擾
    endpoint_params['fields'] = 'business_discovery.username(' + params['ig_username'] + '){\
        username,biography,profile_picture_url,follows_count,followers_count,media_count,\
        media.limit(100){comments_count,like_count,caption,media_url,permalink,timestamp,media_type}}'
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['instagram_account_id']
    return call_api(url, endpoint_params)

class CheckToptagView(APIView):
    def get(self, request, tagname, access_token, instagram_account_id):
        # Instagram Graph API�F�؏��擾
        params = get_credentials()
        ig_username = request.GET.get(key="ig_username")
        tagname = request.GET.get(key="tagname")

        # �{�ԗp
        access_token = request.GET.get(key="access_token")
        instagram_account_id = request.GET.get(key="instagram_account_id")

        # ���[�J���Ŋm�F����ꍇ�͉��L�̃R�����g�A�E�g���O��(.env���K�v)
        # access_token = settings.ACCESS_TOKEN
        # instagram_account_id = settings.USER_ID

        params['access_token'] = access_token
        params['instagram_account_id'] = instagram_account_id
        params['ig_username'] = "mamainstatorisetu"
        # �n�b�V���^�O�ݒ�
        params['tagname'] = tagname
        # �n�b�V���^�OID�擾    
        hashtag_id_response = get_hashtag_id(params)
        # �n�b�V���^�OID�ݒ�
        params['hashtag_id'] = hashtag_id_response['json_data']['data'][0]["id"]

        account_response = get_account_info(params)
        business_discovery = account_response['json_data']['business_discovery']
        username = business_discovery['username']
        biography = business_discovery['biography']
        profile_picture_url = business_discovery['profile_picture_url']
        follows_count = business_discovery['follows_count']
        followers_count = business_discovery['followers_count']
        media_count = business_discovery['media_count']
        media_data = business_discovery['media']['data']

        # ���f�B�AID���X�g�̍쐬
        media_list = [media_data[i]['id'] for i in range(len(media_data))]

        hashtag_media_response = get_hashtag_media(params)
        hashag_data = hashtag_media_response['json_data']["data"]

        # �n�b�V���^�O�g�b�v�̃��f�B�AID���X�g�̍쐬
        toptag_list = [hashag_data[i]['id'] for i in range(len(hashag_data))]

        # ���f�B�AID�̑��݊m�F
        media_set = set(media_list)
        toptag_set = set(toptag_list)
        matched_list = list(media_set & toptag_set)

        matched_medias = [media_data[i] for i in range(len(media_data)) if media_data[i]['id'] in matched_list]

        matched_data = {
            'tagname':tagname,
            'num':len(matched_medias),
            'timestamp':dt.now().strftime('%Y-%m-%d %H:%M:%S'),
            'matched_medias':matched_medias,
        }

        return Response(matched_data)
