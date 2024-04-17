import sys, re, json
from PyQt6.QtWidgets            import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton
from PyQt6.QtWebEngineWidgets   import QWebEngineView
from PyQt6.QtCore               import Qt, QUrl, QByteArray, QJsonDocument
from PyQt6.QtNetwork            import QNetworkAccessManager, QNetworkRequest

class Ui_MainWindow():
    
    
    def setUi(self, MainWidget):
        MainWidget.setObjectName("MainWidget")
        MainWidget.resize(1300, 800)        #窗口宽高
        
        layout = QVBoxLayout()              #定义垂直布局
        
        subayout = QHBoxLayout()            #定义一个水平布局, 是一个子布局
        #增加单行文本框
        self.EditUrl        = QLineEdit()
        self.EditUrl.setText('https://www.zhipin.com/')
        subayout.addWidget(self.EditUrl)
        #增加若干按钮
        self.ButtonGo       = QPushButton('跳转')
        self.ButtonGetHtml  = QPushButton('PC版BOSS直聘-获取HTML')
        self.ButtonNextPage = QPushButton('PC版BOSS直聘-下一页')
        self.ButtonMobile   = QPushButton('移动版BOSS-获取HTML')
        subayout.addWidget(self.ButtonGo)
        subayout.addWidget(self.ButtonGetHtml)
        subayout.addWidget(self.ButtonNextPage)
        subayout.addWidget(self.ButtonMobile)
        layout.addLayout(subayout)
        
        #浏览器控件
        self.browser = QWebEngineView()
        self.browser.settings().setAttribute( self.browser.settings().WebAttribute.JavascriptEnabled, True )
        self.browser.settings().setAttribute( self.browser.settings().WebAttribute.PluginsEnabled, True )
        self.browser.load(QUrl('https://www.zhipin.com/'))
        layout.addWidget(self.browser, 1)
        
        #布局加载
        MainWidget.setLayout(layout)


##==============================================


class MainWidget(QWidget):


    def __init__(self):
        super().__init__()
        #窗口标题
        self.setWindowTitle('获取网页HTML')
        #窗口界面
        self.__ui = Ui_MainWindow()
        self.__ui.setUi(self)
        self.__ui.ButtonGo.clicked.connect(self.__gowebsite)
        self.__ui.ButtonGetHtml.clicked.connect(self.__getHtml)
        self.__ui.ButtonNextPage.clicked.connect(self.__nextPage)
        self.__ui.ButtonMobile.clicked.connect(self.__mobileHtml)
        #浏览器控件网址的变化
        self.__ui.browser.urlChanged.connect(self.__urlchanged)
        #HTTP请求
        self.__manager  = QNetworkAccessManager(self)
        self.__manager.finished.connect(self.replyFinished)
        self.__host     = 'http://192.168.1.212:8000'


    #网址跳转
    def __gowebsite(self):
        address = self.__ui.EditUrl.text()
        if len(address) > 0 and address.find('http')==0:
            self.__ui.browser.load(QUrl(address))


    #浏览器控件网址的变化
    def __urlchanged(self, address):
        print( address )
        self.__ui.EditUrl.setText(address.toString())


    #获取浏览器中网页的HTML
    def __getHtml(self):
        browser = self.__ui.browser
        browser.page().runJavaScript("document.documentElement.outerHTML", self.__getHtml_callback)


    #获取浏览器中网页的HTML, 回调函数
    def __getHtml_callback(self, html):
        print('\n---------------------\n')
        data = self.__zhipin(html)
        if isinstance(data, list) and len(data) > 0:
            for _data in data:
                self.__insert(_data)


    #从BOSS直聘获取工作机会
    def __zhipin(self, html):
        start_symbol    = '<ul class="job-list-box">'
        end_symbol      = '<div class="pagination-area">'
        start_position  = html.find(start_symbol)
        end_position    = html.find(end_symbol)
        if start_position == -1:
            print('{}, not exist' . format(start_symbol))
            return None
        if end_position == -1:
            print('{}, not exist' . format(end_symbol))
            return None
        if start_position > end_position:
            print('start_symbol and end_symbol position is incorrect, {}, {}' . format(start_symbol, end_symbol))
            return None
        start_position  = start_position + len(start_symbol)
        html            = html[start_position:end_position]
        
        rows = re.split(r'<li ka="search_list_\d+" class="job-card-wrapper">', html)
        rows = [i for i in rows if i != '']
        print('fetch rows count {}' . format(len(rows)))
        
        data = []
        for row in rows:
            url_list = re.compile(r'href="(.*)" ka="search_list_jname_').findall(row)
            if len(url_list) != 1:
                print('fetch url failed')
                return None
            url_end = url_list[0].find('?')
            url     = '{}{}' . format('https://www.zhipin.com', url_list[0][0:url_end])
            
            title_list = re.compile(r'<span class="job-name">(.*)</span><span class="job-area-wrapper">').findall(row)
            if len(title_list) != 1:
                print('fetch title failed')
                return None
            title       = title_list[0]
            
            company_list = re.compile(r'custompage">(.*)</a><!----></h3>').findall(row)
            if len(company_list) != 1:
                print('fetch company failed')
                return None
            company     = company_list[0]
            
            salary_list = re.compile(r'<span class="salary">(.*)</span><ul class="tag-list">').findall(row)
            if len(salary_list) != 1:
                print('fetch salary failed')
                return None
            salary      = salary_list[0]
            salary_position = salary.find('K')
            if salary_position == -1:
                print('not exist K in salary, {}' . format(salary))
                continue
            salary2     = salary[0:salary_position]
            salary2_list= salary2.split('-')
            salary_min  = int(salary2_list[0])
            salary_max  = int(salary2_list[1])
            
            if title.lower().find('python')==-1 and title.lower().find('django')==-1 and title.lower().find('flask')==-1 and title.lower().find('tornado')==-1:
                print('python not exist in title, {}' . format(title))
                continue
            if salary_min < 15:
                print('salary_min less than 15, {}' . format(salary))
                continue
            temp                = {}
            temp['url']         = url
            temp['title']       = title
            temp['company']     = company
            temp['salary']      = salary
            temp['salary_min']  = salary_min
            temp['salary_max']  = salary_max
            data.append(temp)
        print('fetch job data count {}' . format(len(data)))
        
        return data


    #向服务器http接口插入数据
    def __insert(self, data):
        print(data)
        sendData= QJsonDocument(data).toJson(QJsonDocument.JsonFormat.Compact)
        url     = QUrl(self.__host + '/job/insert')
        request = QNetworkRequest()
        request.setUrl(url)
        request.setRawHeader( QByteArray(b'Content-Type'), QByteArray(b'application/json; charset=utf-8') )
        self.__manager.post( request, sendData)


    #获取http反馈, 成功返回True, 失败则退出程序
    def replyFinished(self, reply):
        
        error = reply.error()
        if error != reply.NetworkError.NoError:
            print('error, http error')
            return None
        
        result = str(reply.readAll(), 'utf-8')
        result = json.loads(result)
        print(result)
        if result['code'] != 1:
            print('error, code is not one in http response json')
            QApplication.quit()
        
        return True


    #跳转至下一页
    def __nextPage(self):
        browser = self.__ui.browser
        browser.page().runJavaScript("if(document.getElementsByClassName('options-pages').length > 0){let link = document.getElementsByClassName('options-pages')[0].getElementsByTagName('a');link_length = link.length;if(link_length>0){link_length=link_length-1;if(link[link_length].className!=='disabled'){link[link_length].click();}}}")


    #智联招聘, 获取浏览器中网页的HTML
    def __mobileHtml(self):
        browser = self.__ui.browser
        browser.page().runJavaScript("document.documentElement.outerHTML", self.__mobileHtml_callback)


    #获取浏览器中网页的HTML, 回调函数
    def __mobileHtml_callback(self, html):
        print('\n---------------------\n')
        data = self.__mobile(html)
        if isinstance(data, list) and len(data) > 0:
            for _data in data:
                self.__insert(_data)


    #从BOSS直聘mobile站点获取工作机会
    def __mobile(self, html):
        start_symbol    = '<div class="job-list job-list-new"'
        end_symbol      = '<div class="loadmore'
        start_position  = html.find(start_symbol)
        end_position    = html.find(end_symbol)
        if start_position == -1:
            print('{}, not exist' . format(start_symbol))
            return None
        if end_position == -1:
            print('{}, not exist' . format(end_symbol))
            return None
        if start_position > end_position:
            print('start_symbol and end_symbol position is incorrect, {}, {}' . format(start_symbol, end_symbol))
            return None
        start_position  = start_position
        html            = html[start_position:end_position]
        
        rows = re.split(r'<li class="item">', html)
        rows = [i for i in rows if i != '']
        print('fetch rows count {}' . format(len(rows)))
        
        data = []
        for row in rows:
            if row.find('href') == -1:
                continue
            
            url_list = re.compile(r'href="(.*)" ka="job_').findall(row)
            if len(url_list) != 1:
                print('fetch url failed')
                return None
            url_end = url_list[0].find('?')
            if url_end == -1:
                url_end = len(url_list[0])
            url     = '{}{}' . format( 'https://www.zhipin.com', url_list[0][0:url_end] )
            
            title_list = re.compile(r'<span class="title-text">(.*)</span>').findall(row)
            if len(title_list) != 1:
                print('fetch title failed')
                return None
            title       = title_list[0]
            if title.lower().find('python')==-1 and title.lower().find('django')==-1 and title.lower().find('flask')==-1 and title.lower().find('tornado')==-1:
                print('python not exist in title, {}' . format(title))
                continue
            
            company_list= re.compile(r'<span class="company">(.*)</span>').findall(row)
            if len(company_list) != 1:
                print('fetch company failed')
                return None
            company     = company_list[0]
            
            salary_list = re.compile(r'<span class="salary">(.*)</span>').findall(row)
            if len(salary_list) != 1:
                print('fetch salary failed')
                return None
            salary      = salary_list[0]
            salary_position = salary.find('K')
            if salary_position == -1:
                print('not exist K in salary, {}' . format(salary))
                continue
            salary2     = salary[0:salary_position]
            salary2_list= salary2.split('-')
            salary_min  = int(salary2_list[0])
            salary_max  = int(salary2_list[1])
            if salary_min < 15:
                print('salary_min less than 15, {}' . format(salary))
                continue
            
            temp                = {}
            temp['url']         = url
            temp['title']       = title
            temp['company']     = company
            temp['salary']      = salary
            temp['salary_min']  = salary_min
            temp['salary_max']  = salary_max
            data.append(temp)
        print('fetch job data count {}' . format(len(data)))
        
        return data


##==============================================


if __name__ == '__main__':
    app     = QApplication(sys.argv)
    window  = MainWidget()
    window.show()
    sys.exit(app.exec())




