import configparser
from os import walk, rename, mkdir
from os.path import isdir, abspath, basename, dirname, exists
from pathlib import PurePath
from shutil import rmtree
from threading import Thread
from tkinter import filedialog, messagebox, BooleanVar, Checkbutton, Label, Button, Frame
from tkinter.ttk import Combobox

from public import PathManager, names2name, win32_shell_copy


class UnpackDraft(Frame):
    p = PathManager()
    import_path = [p.DESKTOP, ]
    draft_todo = [(p.DESKTOP,), ]
    # 此时还未读取，因此
    draft_target: list[str]
    meta_target: list[str]
    val1: BooleanVar
    val2: BooleanVar
    val3: BooleanVar
    draft_comb: Combobox
    meta_comb: Combobox
    is_only: Checkbutton
    is_save: Checkbutton
    message: Label
    import_button: Button

    def __init__(self, parent, label):
        super().__init__(parent, width=560, height=155)
        self.draft_target = self.p.paths[1][0]
        self.meta_target = [r'{}\metas'.format(self.p.paths[1][0]), ]
        draft_label = Label(self, text='已选草稿：')
        export_label = Label(self, text='素材路径：')
        draft_label.grid(row=0, column=0, pady=10, padx=5)
        export_label.grid(row=1, column=0, pady=10, padx=5)
        self.draft_comb = Combobox(self, width=52, state='readonly')
        self.draft_comb.grid(row=0, column=1, columnspan=2, pady=10, padx=5)
        self.draft_comb.config(values=names2name(self.draft_todo))
        self.draft_comb.current(0)
        self.meta_comb = Combobox(self, width=52)
        self.meta_comb.grid(row=1, column=1, columnspan=2, pady=10, padx=5)
        self.meta_comb.config(values=self.meta_target)
        self.meta_comb.current(0)
        draft_choose = Button(self, text='选取草稿', command=self.choose_draft, width=10)
        draft_choose.grid(row=0, column=3, pady=5, padx=5)
        export_choose = Button(self, text='选择路径', command=self.choose_meta_target, width=10)
        export_choose.grid(row=1, column=3, pady=5, padx=5)
        box_frame = Frame(self, width=520, height=20)
        self.val1, self.val2 = BooleanVar(), BooleanVar()
        # 启动guide的时候就已经检查过config.ini了，因此不再执行检查
        self.p.configer.read('config.ini', encoding='utf-8')
        if self.p.configer.has_section('unpack_setting'):
            if self.p.configer.has_option('unpack_setting', 'is_only'):
                self.val1.set(eval(self.p.configer.get('unpack_setting', 'is_only')))
            if self.p.configer.has_option('unpack_setting', 'is_save'):
                self.val2.set(eval(self.p.configer.get('unpack_setting', 'is_save')))
            if self.p.configer.has_option('unpack_setting', 'import_path'):
                self.import_path.insert(0, self.p.configer.get('unpack_setting', 'import_path'))
        else:
            self.p.configer.add_section('unpack_setting')
            self.p.configer.write(open('config.ini', 'w', encoding='utf-8'))
        is_only = Checkbutton(box_frame, text='仅导入索引', variable=self.val1, padx=10)
        is_only.grid(row=0, column=0)
        is_save = Checkbutton(box_frame, text='保存打开路径', variable=self.val2, padx=10)
        is_save.grid(row=0, column=1)
        # TODO：记住meta路径
        box_frame.grid(row=2, column=0, columnspan=4)
        self.export_button = Button(self, text='一键导入草稿', padx=40,
                                    command=lambda: Thread(target=self._import).start(),
                                    )
        self.export_button.grid(row=3, column=1, columnspan=2, padx=5, pady=5)
        self.message = label
        self.p.read_path()
        if exists(r'{}\metas'.format(self.p.paths[1][0])):
            pass
        else:
            mkdir(r'{}\metas'.format(self.p.paths[1][0]))

    def choose_draft(self):
        # 每次点开选择按钮都刷新草稿列表
        self.p.collect_draft()
        select_temp = filedialog.askdirectory(parent=self,
                                              title='请选择已打包的草稿或其父文件夹',
                                              initialdir=self.import_path[0]
                                              )
        self.pick_out_draft(select_temp)  # 解析任务由专门的方法完成

    def choose_meta_target(self):
        select_temp = filedialog.askdirectory(parent=self,
                                              title='请选择一个地址用于存放本地素材',
                                              initialdir=self.p.paths[1][0]
                                              )
        # 不要把素材导入到工程文件位置，否则可能引发错误
        if isdir(select_temp) and select_temp not in self.p.paths[1]:
            self.meta_target.insert(0, select_temp)
            self.meta_comb.config(values=self.meta_target)
            self.meta_comb.current(0)
            self.message.config(text='素材位置选择完毕')
        else:
            messagebox.showwarning(title='发生错误', message='请选择合适的文件夹！')

    def rewrite_json(self, draft_path: str):
        json_file = ['draft_agency_config.json', 'draft_content.json', 'draft_meta_info.json']
        keys = ['draft_path', 'Data_path', 'install_path', 'meta_path_simp']
        # 旧的素材目录名称需要自己读取、自己分割
        paths_old = []
        configer = configparser.ConfigParser()
        configer.read(r'{}\config.ini'.format(abspath(dirname(draft_path))), encoding='utf-8')
        for key in keys:
            ls_tem = configer.get('paths', key).split(',')
            paths_old.append(sorted(ls_tem, key=lambda i: len(i), reverse=True))
        self.p.read_path()  # 更新了p.paths
        paths_new = self.p.paths[0:-2]  # 目标和源还算是不要冲突比较好，否则两个功能会干扰
        this_draft_target = r'{}\{}'.format(self.meta_target[0], basename(draft_path))
        paths_new.append([this_draft_target, ])
        # 遍历三个文件
        for json in json_file:
            with open(r'{}\{}'.format(draft_path, json), 'r', encoding='utf-8') as f:
                s = f.read()
                # 遍历四种路径，本次草稿位置、安装位置、全局草稿位置、缓存位置
                for j in range(4):
                    for path_old in paths_old[j]:  # 从长到短把路径换掉
                        # json文件中的箭头是posix格式的，必须转换
                        # https://docs.python.org/zh-cn/3/library/pathlib.html#pathlib.PurePath.as_posix
                        path_new = PurePath(paths_new[j][0]).as_posix()
                        s = s.replace(path_old, path_new)  # 统一换为guide提供的第一个
            f.close()
            with open(r'{}\{}'.format(draft_path, json), 'w', encoding='utf-8') as f:
                f.write(s)
            f.close()

    def _import(self):
        # os.path.isdir(self.export_comb.get())防止选择拿空，self.draft_comb.get() in self.todo_history防止不选直接按
        if isdir(self.meta_comb.get()) and self.draft_comb.get() in names2name(self.draft_todo):
            self.p.read_path()
            has_draft = True
            # 一开始设置为桌面只是为了方便用户选取，如果用户真一开始就点导出，那就得按规矩找一找具体的draft在哪里
            if self.draft_comb.get() == basename(self.p.DESKTOP):  # 注意桌面有时可能是中文名
                has_draft = self.pick_out_draft(self.p.DESKTOP)
            if has_draft:
                # 写入导入路径
                if self.val2.get() == 1:
                    self.p.configer.set('unpack_setting', 'import_path', ','.join(self.import_path))
                    self.p.configer.write(open('config.ini', 'w', encoding='utf-8'))
                # 写入配置项
                self.p.configer.set('unpack_setting', 'is_only', str(self.val1.get()))
                self.p.configer.set('unpack_setting', 'is_save', str(self.val2.get()))
                self.p.configer.write(open('config.ini', 'w', encoding='utf-8'))
                self.message.config(text='正在导入...')
                # self.p.paths[4].append([self.meta_comb.get()])
                # 依据组合框的显示的值来确定操作哪一组草稿
                for draft in self.draft_todo[names2name(self.draft_todo).index(self.draft_comb.get())]:
                    meta_path = r'{}\meta'.format(abspath(dirname(draft)))
                    self.p.write_path()
                    self.rewrite_json(draft)
                    win32_shell_copy(draft, r'{}\{}'.format(self.p.paths[1][0], basename(draft)))
                    if self.val1.get() != 1:
                        if exists(meta_path):
                            win32_shell_copy(meta_path, self.meta_target[0])
                            # FileError: [WinError 183] 当文件已存在时，无法创建该文件。
                            if exists(r'{}\{}'.format(self.meta_target[0], basename(draft))):
                                rmtree(r'{}\{}'.format(self.meta_target[0], basename(draft)))
                            rename(r'{}\meta'.format(self.meta_target[0]),
                                   r'{}\{}'.format(self.meta_target[0], basename(draft)))
                        else:
                            self.message.config(text='注意，该草稿没有媒体文件！')
                            messagebox.showinfo('可能遇到了异常', '该工程没有媒体文件\n请在后续步骤中链接素材！')
                self.message.config(text='导入完成！')
        else:
            messagebox.showwarning(title='路径无效', message='请检查路径是否存在！')

    def pick_out_draft(self, import_path: str):
        one_todo = []
        for super_path, sub_path, sub_files in walk(import_path):
            # 别把原来就有的给导进来了
            if 'draft_content.json' in sub_files and super_path not in self.p.paths[1]:
                one_todo.insert(0, super_path)
        if len(one_todo) != 0:
            self.import_path.insert(0, import_path)  # 更新导入路径
            # noinspection PyTypeChecker
            self.draft_todo.insert(0, tuple(one_todo))  # 这行一点问题都没有，而且在另一个模块中工作正常，但Pycharm瞎报错，故禁
            self.draft_comb.config(values=names2name(self.draft_todo))
            self.draft_comb.current(0)
            self.meta_comb.config(values=self.meta_target)
            self.meta_comb.current(0)
            self.message.config(text='草稿选择完毕！')
            return True
        else:
            # 已完成草稿特征检查和非空检查，不需要再更改
            messagebox.showwarning(title='操作有误', message='未找到草稿文件！')
            return False
