from utils import read_txt, log
from typing import List, Tuple
from bs4 import BeautifulSoup
import re
import requests

##### CONFIG AREA START
CUSTOM_HEADER = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.106 Safari/537.36'}
BASE_DIR = './datas/'
NAVER_IDX = 0
ORIGIN_IDX = 1
REMOVE_TAGS = ['script', 'span', 'a', 'strong', 'td', 'b']
REMOVE_PATTERN = [r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
                  r"(재배포\s*금지)"]  # 한 라인을 날려버리는


##### CONFIG AREA END


class Article:
    def __init__(self, _urlTuple, _html=''):
        self.naverUrl, self.originUrl = _urlTuple  # ( Naver URL, 원본 URL )
        self.html: str = _html
        self.title: str = ''
        self.content: BeautifulSoup = ''
        self.result: str = ''
        self.isRemove = False
        if _html == '':
            self.html = self.requests_html()

    def requests_html(self):
        resp = requests.get(self.naverUrl, headers=CUSTOM_HEADER)
        log('s', "GET - {}".format(self.naverUrl))
        return resp.text

    def show_result(self):  # 요약문 HTML 을 보여주는 함수
        """
        self.result 가 str 상태로 [SEP] 구분자로
        나눠져있다고 가정
        :return:
        """
        #### 최소 N개 이상일때만 하는게 있어야할듯
        #### 맨첫줄에 "동영상 뉴스"로 시작하면 잘라버리기 !

        result = self.result.replace('\n', '')

        lineList = []
        for line in result.split('[SEP]'):
            if line.strip() != '':
                lineList.append(line.strip())
        result = '\n\n'.join(lineList)
        # 원본
        tmp = []
        for line in self.content.text.strip().replace('\n', '').split('[SEP]'):
            if line.strip() != '':
                tmp.append(line.strip())
        print('\n\n'.join(tmp))

        print('=' * 100)
        # 수정본
        print(result)

    # Getter
    def get_domain(self):
        return self.originUrl

    def get_url(self):
        return self.naverUrl

    def get_html(self):
        return self.html

    def get_isRemove(self):
        return self.isRemove

    def get_result(self):
        return self.result

    # Setter
    def set_title(self, _title):
        self.title = _title

    def set_content(self, _content):
        self.content = _content

    def set_result(self, _result):
        self.result = _result

    def set_isRemove(self, _isRemove):
        self.isRemove = _isRemove


class BaseParser:
    def __init__(self, _domain=''):
        self.idx = -1
        self.domain = _domain

    def __str__(self):  # repr은 쓸필요없을것같아 이거로 대체
        return "[{}] idx '{}' parser".format(self.idx, self.domain)

    def general_parsing(self, _article: Article):
        # Conver HTML -> BS4 Object
        bs = BeautifulSoup(_article.get_html(), 'lxml')

        # Article area 부분 catch
        content = bs.find('div', id='main_content')

        # Head title ( div > h3 )
        head = content.find('div', class_='article_header')
        try:
            title = head.find('h3', id='articleTitle').text.strip()
            _article.set_title(title)
        except:  # 이경우에 들어오는건 기사가 삭제되었다는거
            log('e', "삭제된기사 : {}".format(_article.get_url()))
            _article.set_isRemove(True)
            return 0

        # Body
        # CASE1. 문장간 띄어쓰기를 <br><br>로 보통쓰길래 \n+[SEP] 으로 바꿔줌
        # CASE2. 본문외 불필요 tag들 decompose
        # CASE3. 이메일, '재배포 금지'라는 Pattern 이 들어가있는 Line 제거
        body = content.find('div', id='articleBodyContents')

        """ CASE1 START"""
        br_modify: str = str(body).replace('<br/> <br/>', '<br/><br/>')
        br_modify: str = br_modify.replace('<br/><br/>', '\n[SEP]\n')
        remove_case1 = BeautifulSoup(br_modify, 'lxml')
        _article.set_content(remove_case1)  # 1차정제본을 원본으로 가정
        """ CASE1 END"""

        """ CASE2 START """
        for tag in REMOVE_TAGS:
            tagNum = len(remove_case1.find_all(tag))
            for _ in range(tagNum):
                try:
                    remove_case1.find(tag).decompose()
                except:
                    pass
        remove_case2 = remove_case1
        """ CASE2 END """

        """ CASE3 START """
        removeList = []
        remove_case2_list = remove_case2.text.split('[SEP]')
        compilePattern = [re.compile(pt) for pt in REMOVE_PATTERN]
        for line in remove_case2_list:
            for cpt in compilePattern:
                if cpt.search(line) != None:  # 매칭
                    removeList.append(line)
                    break
        for r in removeList: remove_case2_list.remove(r)
        remove_case3: str = "[SEP]".join(remove_case2_list)
        """ CASE3 END """

        _article.set_result(remove_case3)
        return 1

    def post_edit(self, _text):  # Base 에는 적용 X
        # 기자 특수문자 제거용
        subPattern = [r"(\w+\s*기자)",
                      r'[@#※ㆍ!』…》▶ⓒ◆◇▲©○●]', ]
        for pt in subPattern:
            _text = re.sub(pt, '', _text)
        return _text


class NewsJoins(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 0

    def parsing(self, _article: Article):
        # 기본으로도 커버가능
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)
        _article.set_result(result)
        return 1


class Yna(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 1

    def parsing(self, _article: Article):
        # 맨첫줄의 (서울=연합뉴스) 정빛나 기자 =  이런부분 떄야함
        # 맨첫줄이 기자요약문
        # 그다음두번째가 우리가 쓸 요약문
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)

        # 추가
        result = re.sub(r"(\(서울=연합뉴스\)\s*=)", '', result)

        _article.set_result(result)
        return 1


class HanKyung(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 2

    def parsing(self, _article: Article):
        # 맨처음 시작할때 [기자 ] 이렇게 1개만 떼버려야함
        # [SEP] 토큰도 다 지워지네
        # 그냥그래서 다시짬
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)

        # 추가
        tmpLines = []
        for line in result.split('[SEP]'):
            line = line.strip()
            if line != '':
                tmpLines.append(line)
        tmpLines[0] = re.sub(r"\[.*?\]", '', tmpLines[0])
        result = "[SEP]".join(tmpLines)
        # result = re.sub(r"\[.*?\]", '', result, count=1)

        _article.set_result(result)
        return 1


class Mt(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 3

    def parsing(self, _article: Article):
        # 머니투데이
        # 맨 윗줄이 기자요약, 없는게 많고
        # 가끔 ] 만 살아남아 짝짞이 안맞는경우가 있음
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)

        # 추가
        tmpLines = []
        for line in result.split('[SEP]'):
            line = line.strip()
            if line != '':
                tmpLines.append(line)
        tmpLines[0] = re.sub(r"\[.*?\]", '', tmpLines[0])
        result = "[SEP]".join(tmpLines)

        _article.set_result(result)
        return 1


class Kmib(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 4

    def parsing(self, _article: Article):
        # 국민일보
        # 무난쓰하네
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)

        # 추가
        _article.set_result(result)
        return 1


class Mk(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 5

    def parsing(self, _article: Article):
        # 매일경제
        # 맨마지막에 [기자] 그런게 있다
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)

        # 추가
        tmpLines = []
        for line in result.split('[SEP]'):
            line = line.strip()
            if line != '':
                tmpLines.append(line)
        tmpLines[-1] = re.sub(r"\[.*?\]", '', tmpLines[-1])
        result = "[SEP]".join(tmpLines)

        _article.set_result(result)
        return 1


class Sbs(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 6

    def parsing(self, _article: Article):
        # SBS
        # 맨아래는 (기획·구성: 심우섭, 장아람 / 디자인: 감호정) 이런식으로 되어있으
        # 동영상 뉴스가 많네 6번인덱스 등등
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)

        # 추가
        tmpLines = []
        for line in result.split('[SEP]'):
            line = line.strip()
            if line != '':
                tmpLines.append(line)
        tmpLines[-1] = re.sub(r"\(.*?\)", '', tmpLines[-1])
        result = "[SEP]".join(tmpLines)

        _article.set_result(result)
        return 1


class News1(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 7

    def parsing(self, _article: Article):
        # 서율뉴스1
        # (서울=뉴스1) 문대현 기자 = 시작하네
        # 앞에서 서울이 아닐수도 세종일수도 고성일수도있음
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)

        # 추가
        result = re.sub(r"(\(\w+=뉴스1\)\s*=)", '', result)

        _article.set_result(result)
        return 1


class Jtbc(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 8

    def parsing(self, _article: Article):
        # JTBC
        # 동영상 뉴스 거르자
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)
        # 추가

        _article.set_result(result)
        return 1


class Chosun(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 9

    def parsing(self, _article: Article):
        # 조선일보
        # [ ]
        # [][][]
        # 이렇게 마지막 두줄에 있음 위것 length 로 짤림
        # 아랫줄은 regex로 짜르자
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)
        # 추가
        tmpLines = []
        for line in result.split('[SEP]'):
            line = line.strip()
            if line != '':
                tmpLines.append(line)
        tmpLines[-1] = re.sub(r"\[.*?\]", '', tmpLines[-1])
        result = "[SEP]".join(tmpLines)

        _article.set_result(result)
        return 1


class Kbs(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 10

    def parsing(self, _article: Article):
        # KBS
        # 동영상 뉴스 떤다
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)
        # 추가

        _article.set_result(result)
        return 1


class Edaily(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 11

    def parsing(self, _article: Article):
        # Edaily
        # 맨처음 [이데일리 김현아 기자] 이런식으로 나온다
        # ? 맨아래 네이버에서 이데일리 빡침해소 청춘뉘우스~ 이런거 뜨는데 지워야하나
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)
        # 추가
        tmpLines = []
        for line in result.split('[SEP]'):
            line = line.strip()
            if line != '':
                tmpLines.append(line)
        tmpLines[0] = re.sub(r"\[.*?\]", '', tmpLines[0])
        result = "[SEP]".join(tmpLines)

        _article.set_result(result)
        return 1


class Asiae(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 12

    def parsing(self, _article: Article):
        # Asiae
        # 맨위 [아시아경제 ] 가 처음 뜬다
        # 맨아래 <경제를 보는 눈, 세계를 보는 창 아시아경제 무단전재 배포금지> 부분도 있음
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)
        # 추가
        tmpLines = []
        for line in result.split('[SEP]'):
            line = line.strip()
            if line != '':
                tmpLines.append(line)
        tmpLines[0] = re.sub(r"\[.*?\]", '', tmpLines[0])
        tmpLines[-1] = re.sub(r"\<.*?\>", '', tmpLines[-1])
        result = "[SEP]".join(tmpLines)

        _article.set_result(result)
        return 1


class Ytn(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 13

    def parsing(self, _article: Article):
        # YTN
        # 동영상 뉴스 지우자
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)
        # 추가

        _article.set_result(result)
        return 1


class BizChosun(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 14

    def parsing(self, _article: Article):
        # biz chosun
        # 맨아래 chosunbiz.com가 들어가네 아니면
        # 두줄정도 [][][] 가 있다
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)
        # 추가
        result = result.replace('chosunbiz.com', '')
        tmpLines = []
        for line in result.split('[SEP]'):
            line = line.strip()
            if line != '':
                tmpLines.append(line)
        tmpLines[-1] = re.sub(r"\[.*?\]", '', tmpLines[-1])
        tmpLines[-2] = re.sub(r"\[.*?\]", '', tmpLines[-2])
        result = "[SEP]".join(tmpLines)

        _article.set_result(result)
        return 1


class Newsis(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 15

    def parsing(self, _article: Article):
        # Newsis
        # 【서울=뉴시스】 =  맨윗줄에 이런거 있음 【 이게 특수문
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)
        # 추가
        result = re.sub(r"(\【서울=뉴시스\】\s*=)", '', result)

        _article.set_result(result)
        return 1


class Sedaily(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 16

    def parsing(self, _article: Article):
        # 서울경제
        # [서울경제]가 거의 맨 첫줄에 뜬다
        # ? 기자를 쓰는 방식이 /연유진기자 economicus@sedaily.com 라고 뒤에서 2번째줄에서 씀
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)
        # 추가
        result = re.sub(r"(\[서울경제\])", '', result)
        _article.set_result(result)
        return 1


class Hani(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 17

    def parsing(self, _article: Article):
        # 한겨례
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)
        # 추가
        _article.set_result(result)
        return 1


class Segye(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 18

    def parsing(self, _article: Article):
        # 세계일보
        # 맨마지막 ⓒ 세상을 보는 눈, 글로벌 미디어 이런글이있음
        # 아랫건 못지우겠음 다 다르다
        # 베이징=이우승 특파원 이런글도
        # 황용호 선임기자
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)
        # 추가
        result = result.replace('세상을 보는 눈, 글로벌 미디어', '')
        _article.set_result(result)
        return 1


class Seoul(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 19

    def parsing(self, _article: Article):
        # 서울신문
        # 맨앞줄이 거의 기자의 요약인데가 많다
        # 맨앞에 [서울신문] 가 있네
        # 맨뒤 [] 도

        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)
        # 추가
        result = re.sub(r"(\[서울신문\])", '', result)
        tmpLines = []
        for line in result.split('[SEP]'):
            line = line.strip()
            if line != '':
                tmpLines.append(line)
        tmpLines[-1] = re.sub(r"\[.*?\]", '', tmpLines[-1])
        result = "[SEP]".join(tmpLines)

        _article.set_result(result)
        return 1


class Imbc(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 20

    def parsing(self, _article: Article):
        # Imbc
        # 동영상 뉴스는 뺴자
        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)
        # 추가

        _article.set_result(result)
        return 1


class Khan(BaseParser):
    def __init__(self, _domain=''):
        super().__init__(_domain)
        self.idx = 21

    def parsing(self, _article: Article):
        # 경향신문

        if super().general_parsing(_article):
            pass
        else:
            return -1
        base_result = _article.get_result()
        result = super().post_edit(base_result)
        # 추가

        _article.set_result(result)
        return 1


def make_parser(_originUrl) -> Article:
    news = _originUrl.split('/')[2].strip()
    parser = None
    if news == 'news.joins.com':        parser = NewsJoins(news)
    elif news == 'yna.kr':              parser = Yna(news)
    elif news == 'www.hankyung.com':    parser = HanKyung(news)
    elif news == 'news.mt.co.kr':       parser = Mt(news)
    elif news == 'news.kmib.co.kr':     parser = Kmib(news)
    elif news == 'news.mk.co.kr':       parser = Mk(news)  # 5
    elif news == 'news.sbs.co.kr':      parser = Sbs(news)
    elif news == 'news1.kr':            parser = News1(news)
    elif news == 'news.jtbc.joins.com': parser = Jtbc(news)
    elif news == 'news.chosun.com':     parser = Chosun(news)
    elif news == 'news.kbs.co.kr':      parser = Kbs(news)  # 10
    elif news == 'www.edaily.co.kr':    parser = Edaily(news)
    elif news == 'view.asiae.co.kr':    parser = Asiae(news)
    elif news == 'www.ytn.co.kr':       parser = Ytn(news)
    elif news == 'biz.chosun.com':      parser = BizChosun(news)
    elif news == 'www.newsis.com':      parser = Newsis(news)  # 15
    elif news == 'www.sedaily.com':     parser = Sedaily(news)
    elif news == 'www.hani.co.kr':      parser = Hani(news)
    elif news == 'www.segye.com':       parser = Segye(news)
    elif news == 'www.seoul.co.kr':     parser = Seoul(news)
    elif news == 'imnews.imbc.com':     parser = Imbc(news) # 20
    elif news == 'news.khan.co.kr':     parser = Khan(news)
    log('s', "Loading ... {}".format(parser))
    return parser


def load_url_by_file(_fileNum) -> List[Tuple[str, str]]:
    """
    File로 부터 신문사들 URL가져옮

    :param _fileNum: 뉴스언론사 index
    :return: zip(naver url, origin url)
    """
    urldatas = read_txt(BASE_DIR + "{}.txt".format(_fileNum))  # naver @@@ origin
    # (naver, origin)
    urlList = list(zip(
        [url.split('@@@')[NAVER_IDX] for url in urldatas],
        [url.split('@@@')[ORIGIN_IDX] for url in urldatas]
    ))
    log('s', "{}.txt 파일에서 {}개 불러옴... Ex) {} ".format(_fileNum, len(urlList), urlList[0][ORIGIN_IDX]))
    return urlList