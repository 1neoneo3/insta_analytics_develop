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
import numpy as np
import itertools
import re

def get_credentials():
    credentials = {}
    credentials['graph_domain'] = 'https://graph.facebook.com/'
    credentials['graph_version'] = 'v9.0'
    credentials['endpoint_base'] = credentials['graph_domain'] + credentials['graph_version'] + '/'
    return credentials

# Instagram Graph APIコール
def call_api(url, endpoint_params):
    data = requests.get(url, endpoint_params)
    response = {}
    response['json_data'] = json.loads(data.content)
    return response

# ハッシュタグID取得
def get_hashtag_id(params):
    endpoint_params = {}
    endpoint_params['user_id'] = params['instagram_account_id']
    endpoint_params['q'] = params['tagname']
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + 'ig_hashtag_search'
    return call_api(url, endpoint_params)

# トップメディア取得
def get_hashtag_media(params):
    endpoint_params = {}
    endpoint_params['user_id'] = params['instagram_account_id']
    endpoint_params['fields'] = 'caption,comments_count,like_count' # comments_count,like_countの追加
    # endpoint_params['limit'] = 50
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['hashtag_id'] + '/top_media'
    return call_api(url, endpoint_params)

# ユーザーアカウント情報取得
def get_account_info(params):
    endpoint_params = {}
    # ユーザ名、プロフィール画像、フォロワー数、フォロー数、投稿数、メディア情報取得
    endpoint_params['fields'] = 'business_discovery.username(' + params['ig_username'] + '){\
        username,biography,profile_picture_url,follows_count,followers_count,media_count,\
        media.limit(100){comments_count,like_count,caption,media_url,permalink,timestamp,media_type}}'
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['instagram_account_id']
    return call_api(url, endpoint_params)

# 対象値と一番近いリストの要素とインデックス取得
def get_nearest_value(list, num):

    idx = np.abs(np.asarray(list) - num).argmin()
    return idx

class BuzztagView(APIView):
    def get(self, request):
        params = get_credentials()
        ig_username = request.GET.get(key="ig_username")
        tagname = request.GET.get(key="tagname")

        # 本番用
        access_token = request.GET.get(key="access_token")
        instagram_account_id = request.GET.get(key="instagram_account_id")


        # ローカルで確認する場合は下記のコメントアウトを外す(.envが必要) 
        # access_token = settings.ACCESS_TOKEN
        # instagram_account_id = settings.USER_ID

        params['access_token'] = access_token
        params['instagram_account_id'] = instagram_account_id
        params['ig_username'] = ig_username
        params['tagname'] = tagname
        
        params['hashtag_id'] = get_hashtag_id(params)['json_data']['data'][0]['id']
        account_response = get_account_info(params)
        
        business_discovery = account_response['json_data']['business_discovery']
        username = business_discovery['username']
        biography = business_discovery['biography']
        profile_picture_url = business_discovery['profile_picture_url']
        follows_count = business_discovery['follows_count']
        followers_count = business_discovery['followers_count']
        media_count = business_discovery['media_count']
        media_data = business_discovery['media']['data']

        # 自分の投稿の平均エンゲージメント数を取得
        ave_engage = 0
        for i in range(media_count):
            if media_data[i].get('media_url'):
                ave_engage += media_data[i]['like_count'] + media_data[i]['comments_count']
        ave_num = ave_engage / media_count
        
        # トップメディアのエンゲージメント数のリストを作成
        response = get_hashtag_media(params)
        length = len(response['json_data']['data'])    
        engage_list = [response['json_data']['data'][i]['comments_count'] + response['json_data']['data'][i]['like_count'] for i in range(length)]

        # 自分の投稿の平均エンゲージメント数と一番近い値のタグリストを取得
        for i in range(len(engage_list)):
            idx = get_nearest_value(engage_list, ave_num)
            caption = response['json_data']["data"][idx]["caption"]                
            hash_tag_list = re.findall('#([^\s→#\ufeff]*)', caption)
            if hash_tag_list:
                break
            else:
                del engage_list[idx]
                continue
            
        like_count = response['json_data']["data"][idx]['like_count']
        comments_count = response['json_data']["data"][idx]['comments_count']
        
        buzz_tag_data = {
            'my_average_engagement': ave_num,
            'nearest_engagement': engage_list[idx],
            'caption': caption,
            'like_count': like_count,
            'comments_count': comments_count,
            'hash_tag_list': hash_tag_list,
        }
        
        return Response(buzz_tag_data)