#!/usr/bin/env python3
# encoding: utf-8

import os
import sys
import zipfile
import shutil
import re
import tempfile
from collections import OrderedDict

from bin.sdat2img import main as _sdat2img

class PathNotFoundError(OSError):
    pass

class WrongFileTypeError(OSError):
    pass

def is_win():
    # 判断是否为Windows系统环境
    return os.name == "nt"

def clean_line():
    # 清行
    exec("sys.stderr.write(\'%%-%ss\\r\' %% \" \")"
         % os.get_terminal_size().columns)

def is_exist_path(path, file_format="", file_type="", file_name=""):
    # 判断路径(文件或目录)是否存在 若不存在则抛出异常
    if not os.path.exists(path):
        raise PathNotFoundError("%s: No such file or directory!" % path)
    # 判断文件类型(后缀)
    if file_format and file_type:
        if file_format == "zip" and zipfile.is_zipfile(path):
            return
        elif path.endswith("." + file_format):
            return
        raise WrongFileTypeError("%s: Not a(n) %s file!" % (path, file_type))
    # 判断文件名
    if file_name:
        if os.path.basename(path) == file_name:
            return
        raise WrongFileTypeError("%s: Not a(n) %s file!" % (path, file_name))

def make_zip(path, file_name):
    # 打包zip文件
    # 打包目录下的所有文件和目录 而并非打包目录本身
    if not os.path.isdir(path):
        raise PathNotFoundError("%s: No such directory!" % path)
    zip_path = os.path.normpath(os.path.join(path, "..", file_name))
    remove_path(zip_path)
    with zipfile.ZipFile(zip_path, "w") as zip:
        for root, dirs, files in os.walk(path, topdown=True):
            for f in files:
                f_fullpath = os.path.join(root, f)
                # diff文件不再压缩(因为已经被gz压缩过了)
                if f.endswith(".p"):
                    zip.write(f_fullpath,
                              arcname=f_fullpath.replace(path, "", 1))
                else:
                    zip.write(f_fullpath,
                              arcname=f_fullpath.replace(path, "", 1),
                              compress_type=zipfile.ZIP_DEFLATED)
    return zip_path

def extract_zip(file_path):
    # 解压zip文件 保存在临时文件夹 并返回文件夹路径
    is_exist_path(file_path, "zip", "ZIP")
    extract_path = tempfile.mkdtemp("_ROM", "GOTAPGS_")
    with zipfile.ZipFile(file_path, "r") as zip:
        zip.extractall(extract_path)
    return extract_path

def extract_br(file_path):
    # 解包*.new.dat.br文件 并返回解压得到的*.new.dat路径
    is_exist_path(file_path, "br", "Brotli")
    extract_path = file_path[:-3]
    os.system(" ".join((
        bin_call("brotli"), "-d", file_path, "-o", extract_path
    )))
    if not os.path.exists(extract_path):
        raise PathNotFoundError("%s: Failed to extract this file!" % file_path)
    return extract_path

def extract_sdat(TRANSFER_LIST_FILE, NEW_DATA_FILE, OUTPUT_IMAGE_FILE):
    # 解包*.new.dat文件
    _sdat2img(TRANSFER_LIST_FILE, NEW_DATA_FILE, OUTPUT_IMAGE_FILE)
    return OUTPUT_IMAGE_FILE

def extract_bootimg(file_path):
    # 解包boot.img文件
    is_exist_path(file_path, file_name="boot.img")
    workdir_bak = os.path.abspath(".")
    bimg_path = os.path.join(os.path.split(file_path)[0], "bootimg_ext")
    file2dir(file_path, bimg_path)
    exe_path = file2dir(bin_call("bootimg.exe"), bimg_path)
    os.chdir(bimg_path)
    exit_code = os.system(" ".join((
        "bootimg.exe", "--unpack-bootimg", "boot.img", ">nul"
    )))
    os.chdir(workdir_bak)
    if exit_code != 0:
        raise Exception("Failed to extract %s with bootimg.exe!" % file_path)
    return os.path.join(bimg_path, "initrd")

def extract_img(file_path):
    # 使用Imgextractor.exe程序解包*.img文件 并返回解压得到的目录路径
    # 用于win环境
    is_exist_path(file_path, "img", "EXT2\\EXT3\\EXT4\\YAFFS2\\CRAMFS image")
    exit_code = os.system(" ".join((
        bin_call("Imgextractor.exe"), file_path, "-i", ">nul"
    )))
    if exit_code != 0:
        raise Exception("Failed to extract %s with Imgextractor.exe!"
                        % file_path)
    return file_path[:-4] + "_"

def mount_img(file_path):
    # 使用sudo mount命令挂载*.img文件 并返回挂载路径
    # 用于Linux环境
    is_exist_path(file_path, "img", "EXT2\\EXT3\\EXT4\\YAFFS2\\CRAMFS image")
    dir_path = os.path.normpath(os.path.join(file_path, "..", "system_"))
    mkdir(dir_path)
    print("We need mount system.img with mount command.")
    print("If you see the password entry prompt, "
          "enter the sudo password to get permission.")
    os.system(" ".join((
        "sudo", "mount", file_path, dir_path, "-t ext4", "-o loop,rw"
    )))
    return dir_path

def get_build_prop(file_path):
    # 解析build.prop文件 生成属性键值字典
    is_exist_path(file_path, file_name="build.prop")
    prop_dic = {}
    with open(file_path, "r", encoding="UTF-8", errors="ignore") as f:
        for line in f.readlines():
            linesp = line.strip()
            if not linesp:
                continue
            if linesp.startswith("#"):
                continue
            if "=" in line:
                k, _, v = linesp.partition("=")
                prop_dic[k] = v
    return prop_dic

def get_statfile(path):
    # 解析由Imgextractor.exe解包*.img时生成的*_statfile.txt文件
    # 生成文件和目录的信息字典
    # 仅用于Windows环境
    save_dic = {}
    openfile = path + "_statfile.txt"
    is_exist_path(openfile)
    with open(openfile, "r", encoding="UTF-8", errors="ignore") as f:
        for line in f.readlines():
            try:
                info = list(line.strip()[line.index("/") + 1:].split())
            except:
                continue
            if len(info) == 4:
                info.append("")
            save_dic[os.path.join(*info[0].split("/"))] = info[1:]
            # info 列表各元素信息:
            # 文件相对路径 uid gid 权限 符号链接(没有则为"")
            # 最终返回的字典 以文件相对路径为key 其他信息的列表为value
    return save_dic

def get_file_contexts(file_path):
    # 解析file_contexts文件 生成属性键值字典
    is_exist_path(file_path)
    # 如果是*.bin文件则先进行转换
    if os.path.basename(file_path).endswith(".bin"):
        fpath = file_path[:-4]
        os.system(" ".join((
            bin_call("sefcontext_decompile"), "-o", fpath, file_path
        )))
    else:
        fpath = file_path
    sel_dic = OrderedDict()
    with open(fpath, "r", encoding="UTF-8", errors="ignore") as f:
        for line in f.readlines():
            linesp = line.strip()
            if linesp.startswith("/system"):
                k, v = linesp.split(maxsplit=1)
                if v.startswith("--"):
                    v = v.split(maxsplit=1)[-1].strip()
                sel_dic[k] = v
                # key中可能会有转义字符\ 实际使用时可能需要剔除
    return sel_dic

def get_selabel(dic, path):
    # 通过检索get_file_contexts函数返回的dic
    # 获取path的SE上下文属性 匹配最后一个结果
    k = ""
    for reg in dic.keys():
        if re.match(reg, path):
            k = dic[reg]
    return k

def get_selabel_linux(path):
    # 获取path的SE上下文属性
    # 仅用于Linux环境
    if os.path.isdir(path):
        path, name = os.path.split(path)
        with os.popen("ls -Z %s" % path) as infos:
            for s in infos.readlines():
                info = s.strip().split()
                if name in info:
                    break
    else:
        with os.popen("ls -Z %s" % path) as infos:
            info = infos.read().strip().split()
    if len(info) > 2:
        return info[3]
    else:
        return info[0]

def parameter_split(line):
    # 对edify脚本的参数进行拆分
    # 拆分得到的列表的第一个元素为函数名
    try:
        start = line.index("(")
        end = line.rindex(")")
    except ValueError:
        raise
    pars = []
    pars.append(line[:start])
    for par in line[start+1:end].split(", "):
        if par.startswith("\""):
            # 有时候得到的字符串会加上引号
            # 所以在这里把它去掉 虽然看起来没什么必要
            par = par[1:-1]
        pars.append(par)
    return pars

def bin_call(program_name):
    return os.path.join(os.path.abspath("."), "bin", program_name)

def mkdir(path):
    # 创建目录
    if os.path.exists(path):
        if not os.path.isdir(path):
            try:
                os.remove(path)
            except:
                pass
        else:
            return
    os.makedirs(path)

def file2file(src, dst, move=False):
    # 复制文件到文件
    # move为True时移动文件而不是复制文件
    mkdir(os.path.split(dst)[0])
    if move:
        shutil.move(src, dst)
    else:
        shutil.copyfile(src, dst)
    return dst

def file2dir(src, dst, move=False):
    # 复制文件到目录(不修改文件名)
    # move为True时复制后删除原文件
    mkdir(dst)
    shutil.copy(src, dst)
    if move:
        os.remove(src)
    return os.path.join(dst, os.path.split(src)[1])

def remove_path(path):
    # 移除文件/目录(如果存在的话)
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)
