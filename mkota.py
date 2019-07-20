#!/usr/bin/env python3
# encoding: utf-8

import sys
import os
import tempfile
import re
from argparse import ArgumentParser

from compare import FL_Compare, compare_build_prop
from fileList import FL
import common as cn
from updater import Updater

__version__ = "v1.1"

class MkOta():

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

        print("\nUnpacking OLD Rom...")
        self.p1_path = cn.extract_zip(self.old_package)
        print("\nUnpacking NEW Rom...")
        self.p2_path = cn.extract_zip(self.new_package)
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

        print("\nStart comparison system files...")
        self.cps = FL_Compare(self.p1_sfl, self.p2_sfl)
        print("\nComparative completion!")
        if self.pt_flag:
            print("\nStart comparison vendor files...")
            self.cpv = FL_Compare(self.p1_vfl, self.p2_vfl)
            print("\nComparative completion!")
        self.model, self.verify_info = self.get_rom_info()
        self.bootimg_block = self.get_bootimg_block()
        self.us = Updater()
        self.updater_init()
        self.cp_files()
        # patch check命令参数列表
        self.patch_check_script_list_sp = []
        # patch 命令参数列表
        self.patch_do_script_list_sp = []
        self.diff_files_patch_init()
        self.diff_files_patch_system()
        if self.pt_flag:
            self.diff_files_patch_vendor()
        self.diff_files_patch_write()

        self.remove_items()

        self.package_extract()
        self.create_symlinks()
        self.set_metadata()

        self.updater_end()

        self.final()

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
        file_list = FL(file_path, is_vendor)
        cn.clean_line()
        print("Search completed\nFound %s files, %s directories"
              % (len(file_list), len(file_list.dirlist)))
        return file_list

    def get_rom_info(self):
        print("\nGetting rom information...")
        p1_prop = cn.get_build_prop(os.path.join(self.p1_sfl.fullpath, "build.prop"))
        p2_prop = cn.get_build_prop(os.path.join(self.p2_sfl.fullpath, "build.prop"))
        model = p2_prop.get("ro.product.device", "Unknown")
        arch = "arm"
        if p2_prop.get("ro.product.cpu.abi") == "x86":
            arch = "x86"
        if p2_prop.get("ro.product.cpu.abi2") == "x86":
            arch = "x86"
        if int(p2_prop.get("ro.build.version.sdk", "0")) >= 21:
            if p2_prop.get("ro.product.cpu.abi") == "arm64-v8a":
                arch = "arm64"
            if p2_prop.get("ro.product.cpu.abi") == "x86_64":
                arch = "x64"
        if arch not in ("arm", "arm64"):
            raise Exception("This tool is only available for arm/arm64 devices. "
                            "This rom's device architecture is: %s" % arch)
        verify_info = compare_build_prop(p1_prop, p2_prop)
        print("\nModel: %s" % model)
        print("\nArch: %s" % arch)
        print("\nRom verify info: %s=%s" % verify_info[:-1])
        return model, verify_info

    def get_bootimg_block(self):
        old_script = os.path.join(self.p2_path, "META-INF", "com",
                                  "google", "android", "updater-script")
        cn.is_exist_path(old_script)
        bootimg_block = ""
        with open(old_script, "r", encoding="UTF-8", errors="ignore") as f:
            for line in f.readlines():
                if line.strip().startswith("package_extract_file"):
                    if "\"boot.img\"" in line:
                        bootimg_block = cn.parameter_split(line.strip())[-1]
        if not bootimg_block:
            raise Exception("Can not get boot.img block!")
        return bootimg_block

    def cp_files(self):
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
        cn.file2dir(cn.bin_call("busybox"), os.path.join(self.ota_path, "bin"))
        cn.file2dir(cn.bin_call("bspatch"), os.path.join(self.ota_path, "bin"))

    def updater_init(self):
        print("\nGenerating script...")
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
        # SP
        # 哈希相同但信息不同的文件
        self.cps.diff_info_files = []
        # 符号链接指向不同的文件
        self.cps.diff_slink_files = []
        # 卡刷时直接替换(而不是打补丁)的文件(名)
        self.cps.ignore_names = {
            "build.prop", "recovery-from-boot.p", "install-recovery.sh",
            "backuptool.functions", "backuptool.sh"
        }
        if self.pt_flag:
            self.cpv.diff_info_files = []
            self.cpv.diff_slink_files = []
            self.cpv.ignore_names = set()
        cn.mkdir(os.path.join(self.ota_path, "patch"))

    def diff_files_patch_system(self):
        if self.cps.diff_files:
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
                # SP
                self.patch_check_script_list_sp.append((f2.spath, f1.sha1, f2.sha1))
                self.patch_do_script_list_sp.append((f2.spath, f2.sha1, f1.sha1, p_spath))
            cn.clean_line()

    def diff_files_patch_vendor(self):
        if self.cpv.diff_files:
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
                # SP
                self.patch_check_script_list_sp.append((f2.spath, f1.sha1, f2.sha1))
                self.patch_do_script_list_sp.append((f2.spath, f2.sha1, f1.sha1, p_spath))
            cn.clean_line()

    def diff_files_patch_write(self):
        self.us.blank_line()
        self.us.ui_print("Unpack Patch Files ...")
        self.us.package_extract_dir("patch", "/tmp/patch")
        self.us.package_extract_dir("bin", "/tmp/bin")
        self.us.add("chmod 0755 /tmp/bin/bspatch")
        self.us.blank_line()
        self.us.ui_print("Check Files ...")
        for arg in self.patch_check_script_list_sp:
            # 差异文件patch check
            self.us.apply_patch_check_sp(*arg)
        self.us.blank_line()
        self.us.ui_print("Patch Files ...")
        for arg in self.patch_do_script_list_sp:
            # 差异文件patch
            self.us.apply_patch_sp(*arg)
        self.us.blank_line()
        self.us.delete_recursive("/tmp/patch")
        self.us.delete_recursive("/tmp/bin")

    def remove_items(self):
        self.us.blank_line()
        self.us.ui_print("Remove Unneeded Files ...")
        # 删除目录
        for d in self.cps.FL_1_isolated_dirs_spaths:
            self.us.delete_recursive(d)
        if self.pt_flag:
            for d in self.cpv.FL_1_isolated_dirs_spaths:
                self.us.delete_recursive(d)
        # 删除文件
        for f in self.cps.FL_1_isolated_files_spaths:
            if f not in self.cps.ignore_del_files_spaths:
                self.us.delete(f)
        if self.pt_flag:
            for f in self.cpv.FL_1_isolated_files_spaths:
                if f not in self.cpv.ignore_del_files_spaths:
                    self.us.delete(f)
        # 差异符号链接目录删除
        for d in self.cps.diff_dirs:
            if d.slink:
                self.us.delete(d.spath)
        if self.pt_flag:
            for d in self.cpv.diff_dirs:
                if d.slink:
                    self.us.delete(d.spath)
        # 差异符号链接文件删除
        for f in self.cps.diff_slink_files:
            self.us.delete(f.spath)
        if self.pt_flag:
            for f in self.cpv.diff_slink_files:
                self.us.delete(f.spath)

    def package_extract(self):
        self.us.blank_line()
        self.us.ui_print("Unpack New Files ...")
        if self.cps.FL_2_isolated_dirs or self.cps.FL_2_isolated_files:
            self.us.package_extract_dir("system", "/system")
        if self.pt_flag:
            if self.cpv.FL_2_isolated_dirs or self.cpv.FL_2_isolated_files:
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
        if self.ota_package_name.startswith("/") or re.match(r"[A-Za-z]:\\*", self.ota_package_name):
            ota_zip_real = self.ota_package_name
        else:
            ota_zip_real = os.path.normpath(os.path.join(os.getcwd(), self.ota_package_name))
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
                    for mdir in ("system_", "vendor_"):
                        os.system("sudo umount %s > /dev/null"
                                  % os.path.join(tempfile.gettempdir(), d, mdir))
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

    parser = ArgumentParser()
    parser.add_argument("old_package", help="old package path")
    parser.add_argument("new_package", help="new package path")
    parser.add_argument("-o", "--output", default="OTA.zip", help=" output OTA package name/path (default OTA.zip)(default: ./OTA.zip)")
    parser.add_argument("-e", "--ext-models", help="additional model that allows for model verification(default: None)")

    args = parser.parse_args()

    MkOta(args.old_package, args.new_package, args.output, args.ext_models)
    sys.exit()
