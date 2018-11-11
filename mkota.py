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

class main():

    def __init__(self, old_package, new_package, ota_package_name, ext_models=None):
        self.old_package = old_package
        self.new_package = new_package
        self.ota_package_name = ota_package_name
        if ext_models is None:
            self.ext_models = tuple()
        else:
            self.ext_models = ext_models
        self.run()

    def run(self):
        self.clean_temp()

        self.unpack_zip()
        self.p1_simg = self.unpack_dat(self.p1_path, is_new=False)
        self.p2_simg = self.unpack_dat(self.p2_path, is_new=True)
        self.pt_flag = self.is_pt()
        if self.pt_flag:
            self.p1_vimg = self.unpack_dat(self.p1_path, is_new=False, is_vendor=True)
            self.p2_vimg = self.unpack_dat(self.p2_path, is_new=True, is_vendor=True)

        self.p1_spath = self.unpack_img(self.p1_simg, is_new=False)
        self.p2_spath = self.unpack_img(self.p2_simg, is_new=True)
        if self.pt_flag:
            self.p1_vpath = self.unpack_img(self.p1_vimg, is_new=False, is_vendor=True)
            self.p2_vpath = self.unpack_img(self.p2_vimg, is_new=True, is_vendor=True)

        self.ota_path = tempfile.mkdtemp("_OTA", "GOTAPGS_")

        self.p1_sfl = self.gen_file_list(self.p1_spath, is_new=False)
        self.p2_sfl = self.gen_file_list(self.p2_spath, is_new=True)
        if self.pt_flag:
            self.p1_vfl = self.gen_file_list(self.p1_vpath, is_new=False, is_vendor=True)
            self.p2_vfl = self.gen_file_list(self.p2_vpath, is_new=True, is_vendor=True)

        self.do_compare()
        self.get_rom_info()
        self.get_bootimg_block()
        self.updater_init()
        self.cp_files_1st()
        self.diff_files_patch_init()
        self.diff_files_patch_system()
        if self.pt_flag:
            self.diff_files_patch_vendor()
        self.diff_files_patch_write()

        self.remove_init()
        self.remove_dirs()
        self.remove_files()
        self.remove_slink_dirs()
        self.remove_slink_files()

        self.package_extract()
        self.create_symlinks()
        self.set_metadata()

        self.updater_end()
        self.updater_write()

        self.final()

    def unpack_zip(self):
        print("\nUnpacking OLD Rom...")
        self.p1_path = cn.extract_zip(self.old_package)
        print("\nUnpacking NEW Rom...")
        self.p2_path = cn.extract_zip(self.new_package)

    def is_pt(self):
        return all((
            os.path.exists(os.path.join(self.p1_path, "vendor.new.dat.br")),
            os.path.exists(os.path.join(self.p2_path, "vendor.new.dat.br"))
        ))

    @staticmethod
    def pars_init(bool_1, bool_2):
        str_1 = "OLD"
        if bool_1:
            str_1 = "NEW"
        str_2 = "system"
        if bool_2:
            str_2 = "vendor"
        return str_1, str_2

    def unpack_dat(self, px_path, is_new, is_vendor=False):
        oon, sov = self.pars_init(is_new, is_vendor)
        if os.path.exists(os.path.join(px_path, "%s.new.dat.br" % sov)):
            print("\nUnpacking %s Rom's %s.new.dat.br..." % (oon, sov))
            cn.extract_br(os.path.join(px_path, "%s.new.dat.br" % sov))
        print("\nUnpacking %s Rom's %s.new.dat..." % (oon, sov))
        px_img = cn.extract_sdat(os.path.join(px_path, "%s.transfer.list" % sov),
                                 os.path.join(px_path, "%s.new.dat" % sov),
                                 os.path.join(px_path, "%s.img" % sov))
        cn.remove_path(os.path.join(px_path, "%s.new.dat.br" % sov))
        cn.remove_path(os.path.join(px_path, "%s.new.dat" % sov))
        return px_img

    def unpack_img(self, img_path, is_new, is_vendor=False):
        oon, sov = self.pars_init(is_new, is_vendor)
        print("\nUnpacking %s Rom's %s.img..." % (oon, sov))
        if cn.is_win():
            spath = cn.extract_img(img_path)
            cn.remove_path(img_path)
        else:
            spath = cn.mount_img(img_path)
        return spath

    def gen_file_list(self, file_path, is_new, is_vendor=False):
        oon, sov = self.pars_init(is_new, is_vendor)
        print("\nRetrieving %s Rom's %s file list..." % (oon, sov))
        px = FL(file_path, is_vendor)
        cn.clean_line()
        print("Search completed\nFound %s files, %s directories"
              % (len(px), len(px.dirlist)))
        return px

    def do_compare(self):
        print("\nStart comparison system files...")
        self.cps = FL_Compare(self.p1_sfl, self.p2_sfl)
        print("\nComparative completion!")
        if self.pt_flag:
            print("\nStart comparison vendor files...")
            self.cpv = FL_Compare(self.p1_vfl, self.p2_vfl)
            print("\nComparative completion!")

    def get_rom_info(self):
        print("\nGetting rom information...")
        self.p1_prop = cn.get_build_prop(os.path.join(self.p1_sfl.fullpath, "build.prop"))
        self.p2_prop = cn.get_build_prop(os.path.join(self.p2_sfl.fullpath, "build.prop"))
        self.model = self.p2_prop.get("ro.product.device", "Unknown")
        self.arch = "arm"
        self.is_64bit = False
        if self.p2_prop.get("ro.product.cpu.abi") == "x86":
            self.arch = "x86"
        if self.p2_prop.get("ro.product.cpu.abi2") == "x86":
            self.arch = "x86"
        if int(self.p2_prop.get("ro.build.version.sdk", "0")) >= 21:
            if self.p2_prop.get("ro.product.cpu.abi") == "arm64-v8a":
                self.arch = "arm64"
                self.is_64bit = True
            if self.p2_prop.get("ro.product.cpu.abi") == "x86_64":
                self.arch = "x64"
                self.is_64bit = True
        self.verify_info = compare_build_prop(self.p1_prop, self.p2_prop)
        print("\nModel: %s" % self.model)
        print("\nArch: %s" % self.arch)
        print("\nRom verify info: %s=%s" % self.verify_info[:-1])

    def get_bootimg_block(self):
        old_script = os.path.join(self.p2_path, "META-INF", "com",
                                  "google", "android", "updater-script")
        cn.is_exist_path(old_script)
        self.bootimg_block = ""
        with open(old_script, "r", encoding="UTF-8", errors="ignore") as f:
            for line in f.readlines():
                if line.strip().startswith("package_extract_file"):
                    if "\"boot.img\"" in line:
                        self.bootimg_block = cn.parameter_split(line.strip())[-1]
        if not self.bootimg_block:
            raise Exception("Can not get boot.img block!")

    def cp_files_1st(self):
        print("\nCopying files...")
        new_bootimg = os.path.join(self.p2_path, "boot.img")
        cn.is_exist_path(new_bootimg)
        cn.file2dir(new_bootimg, self.ota_path)
        for f in self.cps.FL_2_isolated_files:
            sys.stderr.write("Copying file %-99s\r" % f.spath)
            cn.file2file(f.path, os.path.join(self.ota_path, "system", f.rela_path))
        if self.pt_flag:
            for f in self.cpv.FL_2_isolated_files:
                sys.stderr.write("Copying file %-99s\r" % f.spath)
                cn.file2file(f.path, os.path.join(self.ota_path, "vendor", f.rela_path))
        cn.clean_line()
        cn.file2dir(cn.bin_call("applypatch_old"), os.path.join(self.ota_path, "bin"))
        cn.file2dir(cn.bin_call("applypatch_old_64"), os.path.join(self.ota_path, "bin"))

    def updater_init(self):
        print("\nGenerating script...")
        self.us = Updater(self.is_64bit)
        if self.model != "Unknown":
            self.us.check_device(self.model, self.ext_models)
            self.us.blank_line()
        self.us.ui_print("Updating from %s" % self.verify_info[1])
        self.us.ui_print("to %s" % self.verify_info[2])
        self.us.ui_print("It may take several minutes, please be patient.")
        self.us.ui_print(" ")
        self.us.blank_line()
        self.us.ui_print("Remount /system ...")
        self.us.add("[ $(is_mounted /system) == 1 ] || umount /system")
        self.us.mount("/system")
        self.us.add("[ -f /system/build.prop ] || {", end="\n")
        self.us.ui_print(" ", space_no=2)
        self.us.abort("Failed to mount /system!", space_no=2)
        self.us.add("}")
        self.us.blank_line()
        if self.pt_flag:
            self.us.ui_print("Remount /vendor ...")
            self.us.add("[ $(is_mounted /vendor) == 1 ] || umount /vendor")
            self.us.mount("/vendor")
            self.us.blank_line()
        self.us.ui_print("Verify Rom Version ...")
        self.us.add("[ $(file_getprop /system/build.prop %s) == \"%s\" ] || {"
                    % (self.verify_info[0], self.verify_info[1]), end="\n")
        self.us.ui_print(" ", space_no=2)
        self.us.abort("Failed! Versions Mismatch!", space_no=2)
        self.us.add("}")

    def diff_files_patch_init(self):
        # patch check命令参数列表
        self.patch_check_script_list = []
        # patch 命令参数列表
        self.patch_do_script_list = []
        # 哈希相同但信息不同的文件
        self.cps.diff_info_files = []
        # 符号链接指向不同的文件
        self.cps.diff_slink_files = []
        # 卡刷时直接替换(而不是打补丁)的文件(名)
        self.cps.ignore_names = {"build.prop",
                                 "recovery-from-boot.p",
                                 "install-recovery.sh",
                                 "applypatch",}
        if self.pt_flag:
            self.cpv.diff_info_files = []
            self.cpv.diff_slink_files = []
            self.cpv.ignore_names = set()
        cn.mkdir(os.path.join(self.ota_path, "patch"))

    def diff_files_patch_system(self):
        if len(self.cps.diff_files):
            for f1, f2 in self.cps.diff_files:
                if f1.slink != f2.slink:
                    self.cps.diff_slink_files.append(f2)
                    continue
                if f1.sha1 == f2.sha1:
                    self.cps.diff_info_files.append(f2)
                    continue
                if f2.name in self.cps.ignore_names:
                    self.cps.FL_2_isolated_files.append(f2)
                    cn.file2file(f2.path,
                                 os.path.join(self.ota_path, "system", f2.rela_path))
                    continue
                sys.stderr.write("Generating patch file for %-99s\r" % f2.spath)
                temp_p_file = tempfile.mktemp(".p.tmp")
                if not cn.get_bsdiff(f1, f2, temp_p_file):
                    # 如果生成补丁耗时太长 则取消生成补丁 直接替换文件
                    self.cps.FL_2_isolated_files.append(f2)
                    cn.file2file(f2.path,
                                 os.path.join(self.ota_path, "system", f2.rela_path))
                    cn.remove_path(temp_p_file)
                    continue
                p_path = os.path.join(self.ota_path, "patch", "system", f2.rela_path + ".p")
                p_spath = p_path.replace(self.ota_path, "/tmp", 1).replace("\\", "/")
                cn.file2file(temp_p_file, p_path, move=True)
                self.patch_check_script_list.append((f2.spath, f1.sha1, f2.sha1))
                self.patch_do_script_list.append((f2.spath, f2.sha1, len(f2), f1.sha1, p_spath))
            cn.clean_line()

    def diff_files_patch_vendor(self):
        if len(self.cpv.diff_files):
            for f1, f2 in self.cpv.diff_files:
                if f1.slink != f2.slink:
                    self.cpv.diff_slink_files.append(f2)
                    continue
                if f1.sha1 == f2.sha1:
                    self.cpv.diff_info_files.append(f2)
                    continue
                if f2.name in self.cpv.ignore_names:
                    self.cpv.FL_2_isolated_files.append(f2)
                    cn.file2file(f2.path,
                                 os.path.join(self.ota_path, "vendor", f2.rela_path))
                    continue
                sys.stderr.write("Generating patch file for %-99s\r" % f2.spath)
                temp_p_file = tempfile.mktemp(".p.tmp")
                if not cn.get_bsdiff(f1, f2, temp_p_file):
                    self.cpv.FL_2_isolated_files.append(f2)
                    cn.file2file(f2.path,
                                 os.path.join(self.ota_path, "vendor", f2.rela_path))
                    cn.remove_path(temp_p_file)
                    continue
                p_path = os.path.join(self.ota_path, "patch", "vendor", f2.rela_path + ".p")
                p_spath = p_path.replace(self.ota_path, "/tmp", 1).replace("\\", "/")
                cn.file2file(temp_p_file, p_path, move=True)
                self.patch_check_script_list.append((f2.spath, f1.sha1, f2.sha1))
                self.patch_do_script_list.append((f2.spath, f2.sha1, len(f2), f1.sha1, p_spath))
            cn.clean_line()

    def diff_files_patch_write(self):
        self.us.blank_line()
        self.us.ui_print("Unpack Patch Files ...")
        self.us.package_extract_dir("patch", "/tmp/patch")
        self.us.package_extract_dir("bin", "/system/bin")
        self.us.add("chmod 0755 /system/bin/applypatch_old")
        self.us.add("chmod 0755 /system/bin/applypatch_old_64")
        self.us.blank_line()
        self.us.ui_print("Check Files ...")
        for arg in self.patch_check_script_list:
            # 差异文件patch check
            self.us.apply_patch_check(*arg)
        self.us.blank_line()
        self.us.ui_print("Patch Files ...")
        for arg in self.patch_do_script_list:
            # 差异文件patch
            self.us.apply_patch(*arg)
        self.us.blank_line()
        self.us.delete_recursive("/tmp/patch")
        self.us.delete("/system/bin/applypatch_old")
        self.us.delete("/system/bin/applypatch_old_64")

    def remove_init(self):
        self.us.blank_line()
        self.us.ui_print("Remove Unneeded Files ...")

    def remove_dirs(self):
        for d in self.cps.FL_1_isolated_dirs_spaths:
            # 删除目录
            self.us.delete_recursive(d)
        if self.pt_flag:
            for d in self.cpv.FL_1_isolated_dirs_spaths:
                self.us.delete_recursive(d)

    def remove_files(self):
        for f in self.cps.FL_1_isolated_files_spaths:
            # 删除文件
            if f not in self.cps.ignore_del_files_spaths:
                self.us.delete(f)
        if self.pt_flag:
            for f in self.cpv.FL_1_isolated_files_spaths:
                if f not in self.cpv.ignore_del_files_spaths:
                    self.us.delete(f)

    def remove_slink_dirs(self):
        for d in self.cps.diff_dirs:
            # 差异符号链接目录删除
            if d.slink:
                self.us.delete(d.spath)
        if self.pt_flag:
            for d in self.cpv.diff_dirs:
                if d.slink:
                    self.us.delete(d.spath)

    def remove_slink_files(self):
        for f in self.cps.diff_slink_files:
            # 差异符号链接文件删除
            self.us.delete(f.spath)
        if self.pt_flag:
            for f in self.cpv.diff_slink_files:
                self.us.delete(f.spath)

    def package_extract(self):
        self.us.blank_line()
        self.us.ui_print("Unpack New Files ...")
        if len(self.cps.FL_2_isolated_dirs + self.cps.FL_2_isolated_files):
            self.us.package_extract_dir("system", "/system")
        if self.pt_flag:
            if len(self.cpv.FL_2_isolated_dirs + self.cpv.FL_2_isolated_files):
                self.us.package_extract_dir("vendor", "/vendor")

    def create_symlinks(self):
        self.us.blank_line()
        self.us.ui_print("Create Symlinks ...")
        for f in (self.cps.FL_2_isolated_dirs +
                  self.cps.FL_2_isolated_files +
                  self.cps.diff_dirs +
                  self.cps.diff_slink_files):
            # 新增符号链接目录 & 新增符号链接文件 &
            # 差异符号链接目录 & 差异符号链接文件 建立符号链接
            if f.slink:
                self.us.symlink(f.spath, f.slink)
        if self.pt_flag:
            for f in (self.cpv.FL_2_isolated_dirs +
                      self.cpv.FL_2_isolated_files +
                      self.cpv.diff_dirs +
                      self.cpv.diff_slink_files):
                if f.slink:
                    self.us.symlink(f.spath, f.slink)

    def set_metadata(self):
        self.us.blank_line()
        self.us.ui_print("Set Metadata ...")
        for f in (self.cps.FL_2_isolated_dirs +
                  self.cps.FL_2_isolated_files +
                  self.cps.diff_dirs +
                  self.cps.diff_info_files +
                  self.cps.diff_slink_files):
            # 新增目录 & 新增文件 &
            # 差异目录 & 差异信息文件 & 差异符号链接文件 信息设置
            self.us.set_metadata(f.spath, f.uid, f.gid,
                                 f.perm, selabel=f.selabel)
        if self.pt_flag:
            for f in (self.cpv.FL_2_isolated_dirs +
                      self.cpv.FL_2_isolated_files +
                      self.cpv.diff_dirs +
                      self.cpv.diff_info_files +
                      self.cpv.diff_slink_files):
                self.us.set_metadata(f.spath, f.uid, f.gid,
                                     f.perm, selabel=f.selabel)

    def updater_end(self):
        self.us.blank_line()
        self.us.add("sync")
        self.us.umount("/system")
        if self.pt_flag:
            self.us.umount("/vendor")
        self.us.blank_line()
        self.us.ui_print("Flash boot.img ...")
        self.us.package_extract_file("boot.img", self.bootimg_block)
        self.us.blank_line()
        self.us.delete_recursive("/cache/*")
        self.us.delete_recursive("/data/dalvik-cache")
        self.us.blank_line()
        self.us.ui_print("Done!")

    def updater_write(self):
        update_script_path = os.path.join(self.ota_path, "META-INF", "com",
                                          "google", "android")
        cn.mkdir(update_script_path)
        new_ub = os.path.join(update_script_path, "update-binary")
        with open(new_ub, "w", encoding="UTF-8", newline="\n") as f:
            for line in self.us.script:
                f.write(line)
        new_uc = os.path.join(update_script_path, "updater-script")
        with open(new_uc, "w", encoding="UTF-8", newline="\n") as f:
            f.write("# Dummy file; update-binary is a shell script.\n")

    def final(self):
        print("\nMaking OTA package...")
        ota_zip = cn.make_zip(self.ota_path)
        ota_zip_real = os.path.join(os.path.split(self.old_package)[0], self.ota_package_name)
        cn.file2file(ota_zip, ota_zip_real, move=True)

        self.clean_temp()
        print("\nDone!")
        print("\nOutput OTA package: %s !" % ota_zip_real)
        sys.exit()

    @staticmethod
    def clean_temp():
        print("\nCleaning temp files...")
        for d in os.listdir(tempfile.gettempdir()):
            if d.startswith("GOTAPGS_"):
                if not cn.is_win():
                    os.system("sudo umount %s > /dev/null"
                              % os.path.join(tempfile.gettempdir(), d, "system_"))
                cn.remove_path(os.path.join(tempfile.gettempdir(), d))

def adj_zip_name(zip_name):
    new_zip_name = str(zip_name)
    if not re.match(r"[\S]*\.[Zz][Ii][Pp]", new_zip_name):
        new_zip_name += ".zip"
    return new_zip_name

if __name__ == "__main__":

    if sys.version_info[0] != 3:
        sys.stderr.write("\nPython 3.x or newer is required.")
        sys.exit()

    print("\nGeneric OTA Package Generation Script %s\nBy Pzqqt" % __version__)

    if len(sys.argv) >= 3:
        old_package = str(sys.argv[1])
        new_package = str(sys.argv[2])
        ota_package_name = "OTA.zip"
        if len(sys.argv) == 3:
            main(old_package, new_package, ota_package_name)
        if len(sys.argv) == 4:
            if str(sys.argv[3]) != "--ext-models":
                ota_package_name = adj_zip_name(sys.argv[3])
            main(old_package, new_package, ota_package_name)
        if len(sys.argv) >= 5:
            if str(sys.argv[3]) == "--ext-models":
                ext_models = tuple(sys.argv[4:])
            else:
                ota_package_name = adj_zip_name(sys.argv[3])
                ext_models = tuple(sys.argv[5:])
            main(old_package, new_package, ota_package_name, ext_models)
    print("Usage:", os.path.split(__file__)[1],
'''<old_package_path> <new_package_path> [ota_package_name] [--ext-models [model_1] [model_2] ...]

    <old_package_path>                     : old package file path
    <new_package_path>                     : new package file path
    [ota_package_name]                     : custom generated OTA package name (default OTA.zip)
    [--ext-models [model_1] [model_2] ...] : additional model that allows for model verification
''')
    sys.exit()
