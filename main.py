#!-*- coding:utf-8 -*-
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import sys
sys.path.insert(0, 'libs')
import webapp2
from bs4 import BeautifulSoup
import urllib
import urllib2
import json
import re
import os
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch
urlfetch.set_default_fetch_deadline(60)
from google.appengine.ext import db

def hatena_blog_entry(url,result=[],page=1):
    path="/entry/\d{4}/\d{2}/\d{2}/\d{5}"
    path2="/entry/\d{8}/\d{10}"
    reg=re.compile("^"+path)
    reg1=re.compile("^"+path2)
    archive="/archive?page="
    pagenumber=page    
    result=result 
    url=url
    doc=urllib.urlopen(url+archive+str(pagenumber))
    soup=BeautifulSoup(doc)
    result+=([url+dict(i.attrs)["href"] for i in soup.findAll('a', href=reg)])
    result+=([url+dict(i.attrs)["href"] for i in soup.findAll('a', href=reg1)])
    if soup.find("span",'pager-next'):
        pagenumber+=1
        hatena_blog_entry(url,result,pagenumber)
    result=list(set(result))
    result.sort()
    result.reverse()
    title=soup.find('h1',id="title").a.string
    img=soup.find('img', attrs={"class":"profile-icon"})
    return [result,title,img]


def get_title(url):
    doc=urllib.urlopen(url)
    soup=BeautifulSoup(doc)
    title=soup.find("title").string
    return title

def hatena_count(url):
    htn_api = 'http://b.hatena.ne.jp/entry/jsonlite/'
    data = urllib2.urlopen(htn_api+url,timeout=60).read()
    info = json.loads(data)
    if info==None:
        title=get_title(url)
        return [title,0]
    else:
        return [info["title"],int(info["count"])]

def hatena_star(url):
    htn_star_api="http://s.st-hatena.com/entry.count.image?uri="
    data = urllib2.urlopen(htn_star_api+url,timeout=60)
    headers = data.info()
    star=headers.getheaders("X-Hatena-Star-Count")  
    starcount={}
    total=0
    for i in star[0].split(","):
        if len(i) != 0:
            j=i.split("=")
            starcount[j[0]]=int(j[1])
            total+=int(j[1])
    starcount["total"]=total
    return starcount

def sharedcount(url):
    sharedcount_api="http://api.sharedcount.com/?url="
    data=urllib2.urlopen(sharedcount_api+url,timeout=60).read()
    info=json.loads(data)
    return [info["Twitter"],info["Facebook"]["like_count"],info["Facebook"]["share_count"],info["GooglePlusOne"]]

def list_to_graph(lis):
    count=["number",]
    htbcount=["Bookmark",]
    htscount=["Star",]
    twittercount=["Twitter",]
    facebookcount=["Facebook",]
    googlepluscount=["Google+",]
    cnt=1
    for i in lis:
        if cnt%5==0:
            count.append(cnt)
        else:
            count.append("")
        htbcount.append(i[2])
        htscount.append(i[3])
        twittercount.append(i[4])
        facebookcount.append(i[5])
        googlepluscount.append(i[6])
        cnt+=1
    data=[count,googlepluscount,facebookcount,twittercount,htscount,htbcount]
    return data

def hindex(ls):
    ls=ls
    ls.sort()
    ls.reverse()
    print ls
    counter=1
    for i in ls:
        if i < counter:
            counter
            break
        else:
            counter+=1
    return counter-1

class Hindexrank(db.Model):
    urlq = db.StringProperty()
    hatena_index = db. IntegerProperty()
    date = db.DateTimeProperty(auto_now_add=True)

class MainHandler(webapp2.RequestHandler):
    def get(self):
        params={"hindex":"","apiresult":"","data":""}
        fpath = os.path.join(os.path.dirname(__file__),'index.html')
        html = template.render(fpath,params)
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(html)
    def post(self):
        a=self.request.get("url")
        b=self.request.get("count")
        if b=="1":
            c=0
            d=30
        elif b=="2":
            c=30
            d=60
        elif b=="3":
            c=60
            d=90
        elif b=="4":
            c=90
            d=120
        elif b=="5":
            c=120
            d=150
        a=a.rstrip("/")
        htnbcount=[]
        apiresult=[]
        ls,title,img=hatena_blog_entry(a,result=[],page=1)
        for i in ls[c:d]:
            htn=hatena_count(i)
            htnbcount.append(htn[1])
            htns=hatena_star(i)
            snsc=sharedcount(i)
            dic=[htn[0],i,htn[1],htns["total"],snsc[0],snsc[1]+snsc[2],snsc[3]]
            apiresult.append(dic)
        htnindex=hindex(htnbcount)
        data=list_to_graph(apiresult)
        params = {"hindex":htnindex,"apiresult":apiresult,"data":data,"url":a,"title":title,"img":img}
        fpath = os.path.join(os.path.dirname(__file__),'result.html')
        html = template.render(fpath,params)
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(html)
        hindexrank=Hindexrank(urlq=a,hatena_index=htnindex)
        hindexrank.put()




app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)
