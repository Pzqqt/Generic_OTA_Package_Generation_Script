#!/usr/bin/env python3
# encoding: utf-8

from compare import FL_Compare, compare_build_prop
from fileList import FL
import common as cn
from updater import Updater

import sys
import os
import hashlib
import tempfile
import re

__version__ = "v1.0"

def main(old_package, new_package, ota_package_name, ext_models=[]):

    print("\nUnpacking OLD Rom...")
    p1_path = cn.extract_zip(old_package)
    print("\nUnpacking NEW Rom...")
    p2_path = cn.extract_zip(new_package)

    if os.path.exists(os.path.join(p1_path, "system.new.dat.br")):
        print("\nUnpacking OLD Rom's system.new.dat.br...")
        cn.extract_br(os.path.join(p1_path, "system.new.dat.br"))
    print("\nUnpacking OLD Rom's system.new.dat...")
    p1_img = cn.extract_sdat(os.path.join(p1_path, "system.transfer.list"),
                             os.path.join(p1_path, "system.new.dat"),
                             os.path.join(p1_path, "system.img"))
    if os.path.exists(os.path.join(p2_path, "system.new.dat.br")):
        print("\nUnpacking NEW Rom's system.new.dat.br...")
        cn.extract_br(os.path.join(p2_path, "system.new.dat.br"))
    print("\nUnpacking NEW Rom's system.new.dat...")
    p2_img = cn.extract_sdat(os.path.join(p2_path, "system.transfer.list"),
                             os.path.join(p2_path, "system.new.dat"),
                             os.path.join(p2_path, "system.img"))

    print("\nUnpacking OLD Rom's system.img...")
    if cn.is_win():
        p1_spath = cn.extract_img(p1_img)
    else:
        p1_spath = cn.mount_img(p1_img)
    print("\nUnpacking NEW Rom's system.img...")
    if cn.is_win():
        p2_spath = cn.extract_img(p2_img)
    else:
        p2_spath = cn.mount_img(p2_img)

    ota_path = tempfile.mkdtemp("_OTA", "GOTAPGS_")

    print("\nRetrieving OLD Rom's file list...")
    p1 = FL(p1_spath)
    cn.clean_line()
    print("Search completed\nFound %s files, %s directories"
          % (len(p1), len(p1.dirlist)))
    print("\nRetrieving NEW Rom's file list...")
    p2 = FL(p2_spath)
    cn.clean_line()
    print("Search completed\nFound %s files, %s directories"
          % (len(p2), len(p2.dirlist)))

    print("\nStart comparison...")
    compare_pj = FL_Compare(p1, p2)
    print("\nComparative completion!")

    print("\nGetting rom information...")
    p1_prop = cn.get_build_prop(os.path.join(p1_spath, "build.prop"))
    p2_prop = cn.get_build_prop(os.path.join(p2_spath, "build.prop"))
    model = p2_prop.get("ro.product.device", "Unknown")
    arch = "arm"
    is_64bit = False
    if p2_prop.get("ro.product.cpu.abi") == "x86":
        arch = "x86"
    if p2_prop.get("ro.product.cpu.abi2") == "x86":
        arch = "x86"
    if int(p2_prop.get("ro.build.version.sdk", "0")) >= 21:
        if p2_prop.get("ro.product.cpu.abi") == "arm64-v8a":
            arch = "arm64"
            is_64bit = True
        if p2_prop.get("ro.product.cpu.abi") == "x86_64":
            arch = "x64"
            is_64bit = True

    check_flag = compare_build_prop(p1_prop, p2_prop)
    print("\nModel: %s" % model)
    print("\nArch: %s" % arch)
    print("\nRom verify info: %s=%s" % check_flag[:-1])

    print("\nCopying files...")
    new_bootimg = os.path.join(p2_path, "boot.img")
    cn.is_exist_path(new_bootimg)
    cn.file2dir(new_bootimg, ota_path)
    for f in compare_pj.FL_2_isolated_files:
        sys.stderr.write("Copying file %-99s\r" % f.spath)
        cn.file2file(f.path, os.path.join(ota_path, "system", f.rela_path))
    cn.clean_line()

    print("\nGenerating script...")
    old_script = os.path.join(p2_path, "META-INF", "com",
                              "google", "android", "updater-script")
    cn.is_exist_path(old_script)
    bootimg_block = ""
    with open(old_script, "r", encoding="UTF-8", errors="ignore") as f:
        for line in f.readlines():
            if line.strip().startswith("package_extract_file"):
                if "\"boot.img\"" in line:
                    bootimg_block = cn.parameter_split(line.strip())[-1]
    if not bootimg_block:
        raise Exception("Can not generate boot.img flash script!")
    update_script = Updater(is_64bit)
    if model != "Unknown":
        update_script.check_device(model, ext_models)
        update_script.blank_line()
    update_script.ui_print("Updating from %s" % check_flag[1])
    update_script.ui_print("to %s" % check_flag[2])
    update_script.ui_print("It may take several minutes, please be patient.")
    update_script.ui_print(" ")
    update_script.blank_line()
    update_script.ui_print("Remount /system ...")
    update_script.add("[ $(is_mounted /system) == 1 ] || umount /system")
    update_script.mount("/system")
    update_script.add("[ -f /system/build.prop ] || {", end="\n")
    update_script.ui_print(" ", space_no=2)
    update_script.abort("Failed to mount /system!", space_no=2)
    update_script.add("}")
    update_script.blank_line()
    update_script.ui_print("Verify Rom Version ...")
    update_script.add("[ $(file_getprop /system/build.prop %s) == \"%s\" ] || {"
                      % (check_flag[0], check_flag[1]), end="\n")
    update_script.ui_print(" ", space_no=2)
    update_script.abort("Failed! Versions Mismatch!", space_no=2)
    update_script.add("}")
    if len(compare_pj.diff_files):
        update_script.blank_line()
        update_script.ui_print("Unpack Patch Files ...")
        update_script.package_extract_dir("patch", "/tmp/patch")
        update_script.blank_line()
        update_script.ui_print("Check System Files ...")
        patch_script_list = []
        # 哈希相同但信息不同的文件
        compare_pj.diff_info_files = []
        # 符号链接指向不同的文件
        compare_pj.diff_slink_files = []
        # 卡刷时直接替换(而不是打补丁)的文件(名)
        ignore_name_list = ("build.prop", "recovery-from-boot.p",
                            "install-recovery.sh", "services.jar",
                            "RetroMusicPlayer.apk", "ViaBrowser.apk",)
        for f1, f2 in compare_pj.diff_files:
            # 差异文件patch check
            if f1.slink != f2.slink:
                compare_pj.diff_slink_files.append(f2)
                continue
            if f1.sha1 == f2.sha1:
                compare_pj.diff_info_files.append(f2)
                continue
            if f2.name in ignore_name_list:
                compare_pj.FL_2_isolated_files.append(f2)
                cn.file2file(f2.path,
                             os.path.join(ota_path, "system", f2.rela_path))
                continue
            sys.stderr.write("Generating patch file for %-99s\r" % f2.spath)
            temp_p_file = tempfile.mkstemp(".p.tmp")
            bsdiff4.file_diff(f1.path, f2.path, temp_p_file)
            p_path = os.path.join(ota_path, "patch",
                                  "system", f2.rela_path + ".p")
            p_spath = p_path.replace(ota_path, "/tmp", 1).replace("\\", "/")
            cn.file2file(temp_p_file, p_path, move=True)
            update_script.apply_patch_check(f2.spath, f1.sha1, f2.sha1)
            patch_script_list.append((f2.spath, f2.sha1, len(f2),
                                      f1.sha1, p_spath))
        cn.clean_line()
        update_script.blank_line()
        update_script.ui_print("Patch System Files ...")
        for arg in patch_script_list:
            # 差异文件patch命令
            update_script.apply_patch(*arg)
        update_script.delete_recursive("/tmp/patch")
    update_script.blank_line()
    update_script.ui_print("Remove Unneeded Files ...")
    for d in compare_pj.FL_1_isolated_dirs_spaths:
        # 删除目录
        update_script.delete_recursive(d)
    for f in compare_pj.FL_1_isolated_files_spaths:
        # 删除文件
        if f not in compare_pj.ignore_del_files_spaths:
            update_script.delete(f)
    for d in compare_pj.diff_dirs:
        # 差异符号链接目录删除
        if d.slink:
            update_script.delete(d.spath)
    for f in compare_pj.diff_slink_files:
        # 差异符号链接文件删除
        update_script.delete(f.spath)
    update_script.blank_line()
    update_script.ui_print("Unpack New Files ...")
    if len(compare_pj.FL_2_isolated_dirs + compare_pj.FL_2_isolated_files):
        update_script.package_extract_dir("system", "/system")
    update_script.blank_line()
    update_script.ui_print("Create Symlinks ...")
    for f in (compare_pj.FL_2_isolated_dirs +
              compare_pj.FL_2_isolated_files +
              compare_pj.diff_dirs +
              compare_pj.diff_slink_files):
        # 新增符号链接目录 & 新增符号链接文件 &
        # 差异符号链接目录 & 差异符号链接文件 建立符号链接
        if f.slink:
            update_script.symlink(f.spath, f.slink)
    update_script.blank_line()
    update_script.ui_print("Set Metadata ...")
    for f in (compare_pj.FL_2_isolated_dirs +
              compare_pj.FL_2_isolated_files +
              compare_pj.diff_dirs +
              compare_pj.diff_info_files +
              compare_pj.diff_slink_files):
        # 新增目录 & 新增文件 &
        # 差异目录 & 差异信息文件 & 差异符号链接文件 信息设置
        update_script.set_metadata(f.spath, f.uid, f.gid,
                                   f.perm, selabel=f.selabel)
    update_script.blank_line()
    update_script.add("sync")
    update_script.umount("/system")
    update_script.blank_line()
    update_script.ui_print("Flash boot.img ...")
    update_script.package_extract_file("boot.img", bootimg_block)
    update_script.blank_line()
    update_script.delete_recursive("/cache/*")
    update_script.delete_recursive("/data/dalvik-cache")
    update_script.blank_line()
    update_script.ui_print("Done!")

    update_script_path = os.path.join(ota_path, "META-INF", "com",
                                      "google", "android")
    cn.mkdir(update_script_path)
    new_ub = os.path.join(update_script_path, "update-binary")
    with open(new_ub, "w", encoding="UTF-8", newline="\n") as f:
        for line in update_script.script:
            f.write(line)
    new_uc = os.path.join(update_script_path, "updater-script")
    with open(new_uc, "w", encoding="UTF-8", newline="\n") as f:
        f.write("# Dummy file; update-binary is a shell script.\n")

    print("\nMaking OTA package...")
    ota_zip = cn.make_zip(ota_path, ota_package_name)
    ota_zip_real = os.path.join(os.path.split(old_package)[0], ota_package_name)
    cn.file2file(ota_zip, ota_zip_real, move=True)

    print("\nCleaning temp files...")
    if not cn.is_win():
        os.system("sudo umount %s" % p1_spath)
        os.system("sudo umount %s" % p2_spath)
    cn.remove_path(p1_path)
    cn.remove_path(p2_path)
    cn.remove_path(ota_path)

    print("\nDone!")
    print("\nOutput OTA package: %s !" % ota_zip_real)
    sys.exit()

if __name__ == "__main__":

    if sys.version_info[0] != 3:
        sys.stderr.write("\nPython 3.x or newer is required.")
        sys.exit()

    print("\nGeneric OTA Package Generation Script %s\nBy Pzqqt" % __version__)

    try:
        import bsdiff4
    except:
        print("\nPlease use pip(3) to install \"bsdiff4\" "
              "before using this tool.")
        sys.exit()

    # 预清理临时文件目录
    for d in os.listdir(tempfile.gettempdir()):
        if d.startswith("GOTAPGS_"):
            if not cn.is_win():
                os.system("sudo umount %s > /dev/null"
                          % os.path.join(tempfile.gettempdir(), d, "system_"))
            cn.remove_path(os.path.join(tempfile.gettempdir(), d))

    if len(sys.argv) >= 3:
        old_package = str(sys.argv[1])
        new_package = str(sys.argv[2])
        ota_package_name = "OTA.zip"
    if len(sys.argv) == 3:
        main(old_package, new_package, ota_package_name)
    elif len(sys.argv) >= 4:
        # 指定额外的可通过验证的机型代号
        ext_models = []
        if str(sys.argv[3]) == "--ext-models":
            ext_models = sys.argv[4:]
        elif str(sys.argv[4]) == "--ext-models":
            ota_package_name = str(sys.argv[3])
            if not re.match(r"[\S]*\.[Zz][Ii][Pp]", ota_package_name):
                ota_package_name += ".zip"
            ext_models = sys.argv[5:]
        main(old_package, new_package, ota_package_name, ext_models)
    else:
        print("Usage:", os.path.split(__file__)[1],
'''<old_package_path> <new_package_path> [ota_package_name] [--ext-models [model_1] [model_2] ...]

    <old_package_path>                     : old package file path
    <new_package_path>                     : new package file path
    [ota_package_name]                     : custom generated OTA package name (default OTA.zip)
    [--ext-models [model_1] [model_2] ...] : additional model that allows for model verification
''')
        sys.exit()
