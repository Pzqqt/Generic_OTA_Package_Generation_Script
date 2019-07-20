#!/usr/bin/env python3
# encoding: utf-8

import os
import hashlib
import sys

import common as cn

class FL_Base:

    def __init__(self, path, root_path, vendor_flag):
        self.uid = self.gid = self.perm = self.slink = ""
        # 文件绝对路径
        self.path = path
        # 文件"根"路径
        self.root_path = root_path
        self.vendor_flag = vendor_flag
        # 文件父目录路径 & 文件名
        self.pare_path, self.name = os.path.split(path)
        # 文件相对"根"路径的相对路径
        if root_path in self.path:
            self.rela_path = self.path.replace(root_path, "", 1)[1:]
        else:
            self.rela_path = ""
        # 文件在卡刷包中存在的路径
        if self.vendor_flag:
            self.spath = "/vendor/" + self.rela_path.replace("\\", "/")
        else:
            self.spath = "/system/" + self.rela_path.replace("\\", "/")
        self.selabel = ""
        if not cn.is_win():
            self.set_info(self.get_stat(self.path))

    def set_info(self, info_list):
        self.uid, self.gid, self.perm, self.slink = info_list

    @staticmethod
    def get_stat(path):
        # 获取文件uid gid 权限 symlink信息 返回一个四元元组
        # 仅用于Linux环境
        file_stat = os.stat(path, follow_symlinks=False)
        if os.path.islink(path):
            slink = os.readlink(path)
        else:
            slink = ""
        return (file_stat.st_uid, file_stat.st_gid, oct(file_stat.st_mode)[-3:], slink)

class FL_File(FL_Base):

    def __init__(self, path, root_path, vendor_flag):
        super(FL_File, self).__init__(path, root_path, vendor_flag)

        # 计算文件sha1
        if self.slink:
            self.sha1 = ""
        else:
            if not os.access(self.path, os.R_OK):
                os.system("sudo chmod +r %s" % self.path)
            with open(self.path, "rb") as f:
                self.sha1 = hashlib.sha1(f.read()).hexdigest()

    def __eq__(self, obj):
        return all((self.sha1 == obj.sha1,
                    self.uid == obj.uid,
                    self.gid == obj.gid,
                    self.perm == obj.perm,
                    self.slink == obj.slink,
                    self.selabel == obj.selabel))

    def __len__(self):
        return os.stat(self.path).st_size

    def __str__(self):
        return "<File %s>" % self.name

class FL_Dir(FL_Base):

    def __eq__(self, obj):
        return all((self.uid == obj.uid,
                    self.gid == obj.gid,
                    self.perm == obj.perm,
                    self.slink == obj.slink,
                    self.selabel == obj.selabel))

    def __str__(self):
        return "<Dir %s>" % self.name

class FL:

    # 文件列表的类
    # 检索文件时要忽略的文件名列表
    skip_list = (".journal",)

    def __init__(self, fullpath, vendor_flag=False):
        cn.is_exist_path(fullpath)
        self.fullpath = fullpath
        self.vendor_flag = vendor_flag
        self.basepath, self.dirpath = os.path.split(fullpath)

        if cn.is_win():
            self.statfile_info = cn.get_statfile(self.fullpath)
        # 生成文件(FL_File对象)的列表
        self.filelist = []
        # 生成目录(FL_Dir对象)的列表
        self.dirlist = []
        for root, dirs, files in os.walk(self.fullpath, topdown=True):
            for f in files:
                if f in self.skip_list:
                    continue
                fpath = os.path.join(root, f)
                new_f = FL_File(fpath, self.fullpath, self.vendor_flag)
                if cn.is_win():
                    new_f.set_info(self.statfile_info[new_f.rela_path])
                self.filelist.append(new_f)
                sys.stderr.write("Found file %-99s\r" % f)
            for d in dirs:
                dpath = os.path.join(root, d)
                new_d = FL_Dir(dpath, self.fullpath, self.vendor_flag)
                if cn.is_win():
                    new_d.set_info(self.statfile_info[new_d.rela_path])
                self.dirlist.append(new_d)

        cn.clean_line()
        # 生成文件相对路径的列表
        self.file_pathlist = [f.spath for f in self.filelist]
        # 生成目录相对路径的列表
        self.dir_pathlist = [f.spath for f in self.dirlist]

        # 为文件和目录对象设置selabel属性
        if not self.set_selabels(self.basepath):
            if cn.is_win():
                bootimg_ramdisk_path = cn.extract_bootimg(
                    os.path.join(self.basepath, "boot.img"))
                if not self.set_selabels(bootimg_ramdisk_path):
                    raise Exception("Could not find (plat_)file_contexts(.bin)!"
                                    " So we can not get selabel of files!")
            else:
                if os.system("ls -Z > /dev/null") == 0:
                    for f in self.filelist + self.dirlist:
                        f.selabel = cn.get_selabel_linux(f.path)
                else:
                    raise Exception("Can not get selabel with "
                                    "\"ls -Z\" command!")

    def set_selabels(self, fc_basepath):
        fc_path = ""
        if self.vendor_flag:
            fc_tuple = ("vendor_file_contexts", "nonplat_file_contexts",
                        "file_contexts")
        else:
            fc_tuple = ("plat_file_contexts", "file_contexts")
        for fc_name in fc_tuple:
            fc_path_tmp = os.path.join(fc_basepath, fc_name)
            if os.path.exists(fc_path_tmp):
                fc_path = fc_path_tmp
                break
            if os.path.exists(fc_path_tmp + ".bin"):
                fc_path = fc_path_tmp + ".bin"
                break
        if not fc_path:
            return False
        sel_dic = cn.get_file_contexts(fc_path)
        for f in self.filelist + self.dirlist:
            sel = cn.get_selabel(sel_dic, f.spath)
            if sel:
                f.selabel = sel
            else:
                raise Exception("Failed to get selabel for %s!" % f.path)
        return True

    def __len__(self):
        return len(self.filelist)

    def __getitem__(self, i):
        return self.filelist[i]
