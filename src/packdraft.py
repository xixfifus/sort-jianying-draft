from json import load
from os import startfile
from os.path import exists, basename, split, abspath
from shutil import make_archive, rmtree
from time import strftime, localtime
from tkinter import Checkbutton, BooleanVar

import template
from public import names2name, win32_shell_copy


class PackDraft(template.Template):
    # 必须重载这两个变量，否则用父类的构建方法访问的只能是父类的类属性，从而造成子类间的变量混淆
    checks: list[Checkbutton] = []
    vals: list[BooleanVar] = []
    checks_names = ['is_only', 'is_zip', 'is_open', 'is_remember']
    checks_names_display = ['仅导出索引', '打包为单文件', '完成后打开文件', '记住导出路径']
    mould_name = 'pack'
    mould_name_display = '导出草稿'

    def __init__(self, parent, label):
        super().__init__(parent, label)

    def analyse_meta(self, draft_path: str):
        # 每次执行新项目就要清空上次的记录，否则记录会叠加
        self.p.paths[3].clear()
        self.p.paths[4].clear()
        with open('{}\\draft_meta_info.json'.format(draft_path), 'r', encoding='utf-8') as f:
            data = load(f)
            meta_temp = data.pop('draft_materials')
            meta_dic = meta_temp[0]
            meta_list = meta_dic.pop('value')
            for item in meta_list:
                path = item.pop('file_Path')
                if exists(path):
                    # 这些路径仅用于替换，因此顺序不重要，直接用了append
                    self.p.paths[3].append(path)
                    self.p.paths[4].append(split(path)[0])
        self.p.paths[4] = list(set(self.p.paths[4]))
        self.p.write_path()
        # 必须及时关闭，否则f时刻被占用，不可替换内部资源
        f.close()

    def main_fun(self):
        # 写入导出路径
        if self.vals[3].get() == 1:
            self.p.configer.set('pack_setting', 'export_path', ','.join(self.export_path))
            self.p.configer.write(open('config.ini', 'w', encoding='utf-8'))
        for draft in self.drafts_todo[names2name(self.drafts_todo).index(self.draft_comb.get())]:
            # 不能使用冒号，否则OSError: [WinError 123] 文件名、目录名或卷标语法不正确
            suffix = strftime('%m.%d.%H-%M-%S', localtime())
            filepath = '{}\\{}-收集的草稿-{}'.format(self.export_path[0], basename(draft), suffix)
            self.analyse_meta(draft)
            win32_shell_copy(draft, '{}\\{}'.format(filepath, basename(draft)))
            win32_shell_copy(abspath('config.ini'), '{}\\config.ini'.format(filepath))
            # 未选中“仅导出索引，就导出素材”
            if self.vals[0].get() != 1:
                # 复制的是文件，则复制后也应当是文件
                for path in self.p.paths[3]:
                    win32_shell_copy(path, '{}\\meta\\{}'.format(filepath, basename(path)))
                    # TODO:这里有风险，有时会有重名文件覆盖
            if self.vals[1].get() == 1:
                self.message.config(text='正在压缩单文件...')
                make_archive(filepath, 'zip', filepath)
                rmtree(filepath)
                self.message.config(text='草稿文件创建成功！')
            if self.vals[3].get() == 1:
                startfile(self.export_path[0])
        self.message.config(text='草稿打包完毕！')
