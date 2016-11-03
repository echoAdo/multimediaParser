#encoding=utf-8

import string
import sys
import os
import os.path
import subprocess
import shutil
from xml.etree import ElementTree as ET

def runShellCommand(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT):
    """run linux shell command, return result or error"""
    p = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, shell=True)
    returnCode = p.wait()
    result = p.communicate()
    if returnCode:
        print 'subProcess execute failed (%s) ' % cmd
        return None

    return result[0]

class FileProcess:
    """"XML format mediainfo parser"""
    """container_vCodec_vProfile_vResolution_vFrameRate_vBitRate+aCodec_aProfile_aSampleRate_aChannel_duration.fileSuffix"""

    def __init__(self, src, dst):
        self.srcDirectory = src
        if dst[-1] != '/': self.dstDirectory = dst + '/'
        else:              self.dstDirectory = dst
        self.srcFile = ''
        self.keyword = ['vFormat', 'vProfile', 'vResolution', 'vFrameRate', 'gBitRate',\
                        'aFormat', 'aProfile', 'aSampleRate', 'aChannels', 'gDuration']

    def browserDirectory(self):
        list_dirs = os.walk(self.srcDirectory)
        for root, dirs, files in list_dirs:
            for f in files:
                self.srcFile = os.path.join(root, f)
                shellCmd  =  "mediainfo --output=XML " + "'" + self.srcFile + "'"
                xml = runShellCommand(shellCmd)
                if xml is None:
                    continue

                srcFileInfo = MediaXMlParser().parser(xml)
                targetPath, targetFile = self.makeTargetFile(srcFileInfo, f)
                if targetPath == None or targetFile == None:
                    print  self.srcFile + " is not video/audio"
                    continue

                print targetFile + ':' + self.srcFile

                if not os.path.exists(targetPath):
                    os.makedirs(targetPath)

                try:
                    shutil.copy(self.srcFile, targetPath+'/'+targetFile)
                except IOError, e:
                    print e

    def dictionary2String(self, dic):
        dstString = ''
        for item in self.keyword:
            if dic.has_key(item):
                separator = '_'
                if item == 'aFormat' and dic.has_key('vFormat'):
                    separator = '+'
                dstString = dstString + separator + dic.get(item)

        return dstString

    def makeTargetFile(self, info, name):
        fileSuffix = name.split(".")[-1]
        container = fileSuffix.upper()
        path = name = None

        if info.has_key('vFormat'):
            path = self.dstDirectory + 'VIDEO' + os.sep + container + os.sep + info.get('vFormat')
            name =  container + self.dictionary2String(info) + '.' + fileSuffix
        elif info.has_key('aFormat'):
            path = self.dstDirectory + 'AUDIO'  + os.sep + container + os.sep + info.get('aFormat')
            name =  container + self.dictionary2String(info) + '.' + fileSuffix
        else:
            return path, name

        return path, name

class MediaXMlParser:
    """"XML format mediainfo parser"""
    iMap = [('HE-AAC-LC','HE-AAC'), ('HE-AACv2-HE-AAC-LC' , 'HE-AACv2'), \
            ('MPEG Video','MPEG'), ('AVS Video', 'AVS'), ('MPEG-4 Visual','MPEG4'),\
            ('Sorenson Spark', 'MPEG4')]
            #('MA / Core', 'MA-Core'), ('ES Discrete / Core', 'ES-Discrete-Core')]

    def __init__(self):
        self.mediaInfo = {}

    def parser(self, xmlString):
        """
        tree = ElementTree.parse("xmlMedia.xml")
        root = tree.getroot()
        p = root.find('./File').findall('./track')
        """
        root = ET.fromstring(xmlString)
        parent = root.findall('./File/track')

        for ele in parent:
            if self.hasTypeAttribute(ele, 'General'):
                self.getGeneralInfo(ele)
            elif self.hasTypeAttribute(ele, 'Video'):
                self.getVideolInfo(ele)
            elif self.hasTypeAttribute(ele, 'Audio'):
                self.getAudioInfo(ele)
            #print ele.attrib

        #Don't care bitRate parameter for audio file
        if not self.mediaInfo.has_key('vfFormat') and self.mediaInfo.has_key('gBitRate'):
            del self.mediaInfo['gBitRate']

        """
        for item in self.mediaInfo:
            print item + " : " + self.mediaInfo[item]
        """
        return self.mediaInfo

    def hasTypeAttribute(self, element, value):
        return element.attrib.has_key('type') and (string.find(element.attrib['type'], value) != -1)

    def getHumanReadbleFromat(self, key):
        for item in self.iMap:
            if item[0] == key:
                return item[1]

        return key

    # Video Real Player 9 --> RV9, Audio Real Player 9 --> RA9
    def transformRealCodec(self, key, codec, prefix):
        if self.mediaInfo.has_key(key):
            codecID = self.mediaInfo.get(key)
            begin = codecID.find('Real Player')   
            if begin != -1:
                value = prefix + codecID[begin:].replace('Real Player ', '')
                self.mediaInfo.update({codec:value})
                del self.mediaInfo[key]

    def getGeneralInfo(self, element):
        for child in element.getchildren():
            if child.tag == "Duration":
                self.mediaInfo.update({'gDuration':child.text.replace(' ', '')})
            elif child.tag == "Overall_bit_rate":
                self.mediaInfo.update({'gBitRate':child.text.replace(' ', '')})

            #print child.tag,':',child.text

    def getVideolInfo(self, element):
        for child in element.getchildren():
            if child.tag == "Format":
                self.mediaInfo.update({'vFormat':self.getHumanReadbleFromat(child.text)})
            elif child.tag == "Format_profile":
                str = child.text.replace(' ', '').replace('/', '-')
                self.mediaInfo.update({'vProfile':self.getHumanReadbleFromat(str)})
            elif child.tag == "Codec_ID":
                self.mediaInfo.update({'vCodecID':child.text})
            elif child.tag == "Codec_ID_Info":
                self.mediaInfo.update({'vCodecIDInfo':child.text})
            elif child.tag == "Bit_rate":
                self.mediaInfo.update({'vBitRate':child.text.replace(' ', '')})
            elif child.tag == "Width":
                str = child.text.replace(' ', '')
                self.mediaInfo.update({'vWidth':str[0:str.find('pixels')]})
            elif child.tag == "Height":
                str = child.text.replace(' ', '')
                self.mediaInfo.update({'vHeight':str[0:str.find('pixels')]})
            elif child.tag == "Frame_rate":
                """Format: 24.000 fps / 23.967(24000/1001) fps  --> 24fps / 24.967fps"""
                str = child.text.split(' ')[0]
                end = len(str)
                if str.find('.000') != -1:
                    end = str.find('.000')
                elif str.find('(') != -1:
                    end = str.find('(')
                fr = str[0:end] + 'fps'
                self.mediaInfo.update({'vFrameRate':fr})

             #print child.tag,':',child.text

        if self.mediaInfo.has_key('vWidth') and self.mediaInfo.has_key('vHeight'):
            resolution = self.mediaInfo.get('vWidth') + 'x' + self.mediaInfo.get('vHeight')
            self.mediaInfo.update({'vResolution':resolution})
        if (self.mediaInfo.get('vFormat', 'None') == 'JPEG'): #and (self.mediaInfo.get('vCodecID', 'None') == 'MJPG'):
            self.mediaInfo.update({'vFormat':'MJPEG'})

        self.transformRealCodec('vCodecIDInfo', 'vFormat', 'RV')

    def getAudioInfo(self, element):
        if self.mediaInfo.has_key('aFormat'):
            #print 'Only extract the first Audio Track. Others discard....'
            return

        for child in element.getchildren():
            if child.tag == "Format":
                self.mediaInfo.update({'aFormat':self.getHumanReadbleFromat(child.text).upper()})
            elif child.tag == "Format_profile":
                str = child.text.replace(' ', '').replace('/', '-')
                self.mediaInfo.update({'aProfile':self.getHumanReadbleFromat(str)})
            elif child.tag == "Codec_ID_Info":
                self.mediaInfo.update({'aCodecIDInfo':child.text})
            elif child.tag == "Channel_s_":
                end = len(child.text)
                if child.text.find('/') != -1:
                    end = child.text.find('/')
                str = child.text[0:end].replace(' ', '')
                self.mediaInfo.update({'aChannels':str})
            elif child.tag == "Sampling_rate":
                self.mediaInfo.update({'aSampleRate':child.text.replace(' ', '')})

            #print child.tag,':',child.text

        # Layer 3 --> MP3
        if self.mediaInfo.get('aFormat', 'None')  == 'MPEG AUDIO':
            aCodec = ''
            profile = self.mediaInfo.get('aProfile', 'None')
            if   profile == 'Layer2': aCodec = 'MP2'
            elif profile == 'Layer3': aCodec = 'MP3'
            elif profile == 'Layer1': aCodec = 'MP1'

            if aCodec != '':
                self.mediaInfo.update({'aFormat':aCodec})
                del self.mediaInfo['aProfile']

        self.transformRealCodec('aCodecIDInfo', 'aFormat', 'RA')

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print "Usage:\n    python MediaSource.py srcDirectory dstDirectory";
        exit();

    obj_fileProcess = FileProcess(sys.argv[1], sys.argv[2])
    obj_fileProcess.browserDirectory()

