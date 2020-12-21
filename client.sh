#!/bin/bash

token="$(curl -d "user=ngld&password=minkaV_1" 'https://api.fsnebula.org/api/1/login' | jq .token | cut -d '"' -f 2)"
url="https://api.fsnebula.org/api/1/$1"
shift

exec curl -H "X-KN-Token: $token" "$@" "$url"

