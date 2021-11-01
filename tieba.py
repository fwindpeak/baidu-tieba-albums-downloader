#!/usr/bin/env python3
#-*- coding: utf-8 -*-
import urllib,re
import urllib.request
import urllib.parse
import os,os.path
import time
import threading
import sys
import logging
import requests
 
IS_DEBUG = False
MULTI_THREAD = False
MAX_Thread = 20
 
tieba_info_fp = ""
 
#tbName = raw_input("输入贴吧名称：")
tbName = ""
tieba_url_base = "http://tieba.baidu.com"
pgUrl_base="http://tieba.baidu.com/photo/g?kw="
photo_url_base = "http://imgsrc.baidu.com/forum/pic/item/"
 
BLOCK_SIZE = 4096
threadLock = threading.Lock()
 
# 打印信息到文件和屏幕
def print_f(msg):
    global tieba_info_fp
    print(msg)
    tieba_info_fp.write(msg+'\n')
    tieba_info_fp.flush()
 
def download_file(url,path):
    if os.path.isfile(path):
        return
    r = urllib.request.urlopen(url)
    fileName = ""
    if path != "":
        fileName = path
    elif r.info().has_key('Content-Disposition'):
        fileName = r.info()['Content-Disposition'].split('filename=')[1]
        fileName = fileName.replace('"', '').replace("'", "")
    else:
        fileName = url[url.rfind('/')+1:]
         
    if os.path.isfile(fileName):
        return
    else:
        file_length = int(r.info()['Content-Length'])
        download_size=0
        f = open(fileName, 'wb')
        try:
            while download_size<file_length:
                dat = r.read(BLOCK_SIZE)
                l = len(dat)
                if l>0:
                    f.write(dat)
                    download_size += l
                else:
                    f.close()
                    os.remove(fileName)
                    raise Exception("time out")
        except Exception as e:
            f.close()
            os.remove(fileName)
            raise e
        finally:
            f.close()
 
class MultiDownload(threading.Thread):
    def __init__(self,dat):
        threading.Thread.__init__(self)
        self.dat = dat
    def run(self):
        while 1:
            pos,url,path = self.dat.start_one()
            if pos == None:
                break
            try:
                download_file(url,path)
                self.dat.end_one(pos)
            #出错标记为未下载
            except Exception as e:
                self.dat.renew_one(pos)
                print(url,e)
                 
 
class DData:
    def __init__(self):
        self.pos = 0
        self.url = []
        self.path = []
        #0 1 2
        self.status = []
 
    def add(self,url,path):
        self.url.append(url)
        self.path.append(path)
        self.status.append('0')
        self.pos += 1
 
    #获取一条未下载的数据，并设置为1（正在下载），返回pos，所有都下载完返回None
    def start_one(self):
        try:
            pos = self.status.index('0')
            threadLock.acquire()
            self.status[pos] = '1'
            threadLock.release()
            return pos,self.url[pos],self.path[pos]
        except ValueError:
            return None,None,None
 
    #结束一条下载
    def end_one(self,pos):
        threadLock.acquire()
        self.status[pos] = '2'
        threadLock.release()
 
    #标记未下载一条下载
    def renew_one(self,pos):
        threadLock.acquire()
        self.status[pos] = '0'
        threadLock.release()
 
def multi_download_run(url_list,path_list=[],MAX_Thread=10):
    dat = DData()
    for i in range(len(url_list)):
        if path_list==[]:
            fn = url[url.rfind('/')+1:]
            path = os.path.join(os.getcwd(),fn)
        else:
            path = path_list[i]
        dat.add(url_list[i],path)
    threads = []
    for i in range(MAX_Thread):
        threads.append(MultiDownload(dat))
    for t in threads:
        t.start()
    for t in threads:
        t.join()
 
def multi_download(pic_list):
    url_list = []
    path_list =[]
    for id in pic_list:
        fn = id + ".jpg"
        url = photo_url_base + fn
        path = os.path.join(os.getcwd(),fn)
        url_list.append(url)
        path_list.append(path)
    multi_download_run(url_list,path_list,MAX_Thread=10)
 
# 进入子目录,如果不存在则创建
def chsubdir(dirname):
    cwd=os.getcwd()
    subdir = os.path.join(cwd,dirname)
    if os.path.exists(subdir) == False:
        os.mkdir(subdir)
    os.chdir(subdir)
 
## 读取相册
def read_album(tid,name):
    chsubdir(name)
    if IS_DEBUG == True:
        return
    url= 'http://tieba.baidu.com/photo/bw/picture/guide?kw=%s&tid=%s&see_lz=1&from_page=0&alt=jview&next=15'%(tbName,tid)
    # print url
    pageData = requests.get(url).text
    #print pageData
    p = re.compile('"pic_amount":(\d+),')
    pic_amount = p.search(pageData).group(1)
    print_f ("┗━━"+name + ' '+pic_amount + '张')
    p = re.compile('"original":{"id":"(\S+?)"')
    find_list = p.findall(pageData)
    pic_list = find_list
    i= len(pic_list)
    pic_amount=int(pic_amount) # 转化为整数型
    while pic_amount>i:
        #print i
        url2 = url+"&prev=0&pic_id="+pic_list[-1]
        pageData = requests.get(url2).text
        p = re.compile('"original":{"id":"(\S+?)"')
        find_list = p.findall(pageData)
        pic_list = pic_list + find_list[1:]
        i=len(pic_list)
    multi_download(pic_list)
     
## 读取相册集
def read_catalog(url,name):
    if name != '':
        chsubdir(name)
        print_f(name)
    page = 1
    while 1:
        url_page = "%s&pn=%d"%(url,page)
        pageData = requests.get(url_page).text
        p = re.compile ('<div class="grbm_ele_title.+?href="(\S+?)".+?title="(.+?)"',re.S)
        result = p.findall(pageData)
        root_dir = os.getcwd()
        if len(result)==0:
            break
        else :
            for a in result:
                #cUrl = tieba_url_base + a[1]
                tid=a[0][3:]
                cName = a[1]
                os.chdir(root_dir)
                read_album(tid,cName)
            page += 1
 
## 读取根目录信息
def read_root(url,name):
    global tieba_info_fp
    chsubdir(name)
    try:
        tieba_info_fp = open('%s吧信息.txt'%(name),"w")
        print_f('【%s】'%(name))
        pageData = requests.get(url).text
    #1、读取总相片数量
        p = re.compile ('<div class="picture_amount_total">共有图片 (\d+?) 张</div>',re.S)
        result = p.findall(pageData)
        picture_amount_total = 0
        if len(result) == 0:
            print_f('可能这个贴吧不存在，或者这个程序已经不能使用')
            tieba_info_fp.close()
            return
        else:
            picture_amount_total = int(result[0])
        print_f('共有图片 %d 张'%(picture_amount_total))
         
    #2、先尝试存在相册分类的情况
        p = re.compile ('<li class="catalog_li_normal.+?href="(\S+?)".+?catalog_a_inner">(.+?)<span class="catalog_a_amount">\((\d+?)\)</span>',re.S)
        result = p.findall(pageData)
        root_dir = os.getcwd()
        if len(result)>0:
            for a in result:
                cat_id = a[0][10:]
                cat_name = a[1]
                os.chdir(root_dir)
                cat_url = url+ "&cat_id=" + cat_id
                read_catalog(cat_url,cat_name)
    #3、没有相册分类，直接获取所有相册目录
        else:
            cat_url = url+ "&cat_id=all"
            read_catalog(cat_url,'')
    except Exception as e:
        print(e)
        print(sys.exc_info())
        logging.exception("logging...")
    finally:
        tieba_info_fp.close()
     
         
def main():
    global tbName
    args = len(sys.argv)
    if args>1:
        for i in range(1,args):
            tbName = sys.argv[i]
            print(sys.argv[i])
            pgUrl = pgUrl_base + tbName
            read_root(pgUrl,tbName)
    else:
        tbName = input("输入贴吧名称：")
        pgUrl = pgUrl_base + tbName
        read_root(pgUrl,tbName)
 
if __name__ == '__main__':
    main()
 
 
