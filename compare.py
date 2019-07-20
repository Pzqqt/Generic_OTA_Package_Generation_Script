#!/usr/bin/env python3
# encoding: utf-8

from fileList import FL

class FL_Compare:

    def __init__(self, FL_1, FL_2):
        if not all((isinstance(FL_1, FL), isinstance(FL_2, FL))):
            raise ValueError("The parameters must be FL object!")
        self.FL_1 = FL_1
        self.FL_2 = FL_2

        print("\nCalculating unique dirs...")
        self.__gen_isolated_dirlist()
        print("\nCalculating unique files...")
        self.__gen_isolated_filelist()
        print("\nComparing shared dirs...")
        self.__dir_compare()
        print("\nComparing shared files...")
        self.__file_compare()

    def __gen_isolated_dirlist(self):
        self.FL_1_isolated_dirs = [d for d in self.FL_1.dirlist
                                   if d.spath not in self.FL_2.dir_pathlist]
        self.FL_2_isolated_dirs = [d for d in self.FL_2.dirlist
                                   if d.spath not in self.FL_1.dir_pathlist]
        self.FL_1_isolated_dirs_spaths = \
            [d.spath for d in self.FL_1_isolated_dirs]
        self.FL_2_isolated_dirs_spaths = \
            [d.spath for d in self.FL_2_isolated_dirs]
        print("\nThese dirs were deleted in the new package:")
        if self.FL_1_isolated_dirs:
            for d in self.FL_1_isolated_dirs:
                print("    " + d.spath)
        else:
            print("\n    (None)")
        print("\nThese dirs are added in the new package:")
        if self.FL_2_isolated_dirs:
            for d in self.FL_2_isolated_dirs:
                print("    " + d.spath)
        else:
            print("\n    (None)")

    def __gen_isolated_filelist(self):
        self.FL_1_isolated_files = []
        self.ignore_del_files = []
        for f in self.FL_1:
            if f.spath not in self.FL_2.file_pathlist:
                for d in self.FL_1_isolated_dirs_spaths:
                    if d in f.spath:
                        self.ignore_del_files.append(f)
                self.FL_1_isolated_files.append(f)
        self.FL_2_isolated_files = [f for f in self.FL_2
                                    if f.spath not in self.FL_1.file_pathlist]
        self.FL_1_isolated_files_spaths = \
            [f.spath for f in self.FL_1_isolated_files]
        self.FL_2_isolated_files_spaths = \
            [f.spath for f in self.FL_2_isolated_files]
        self.ignore_del_files_spaths = \
            [f.spath for f in self.ignore_del_files]
        print("\nThese files were deleted in the new package:")
        if self.FL_1_isolated_files:
            for f in self.FL_1_isolated_files:
                if f.spath not in self.ignore_del_files_spaths:
                    print("    " + f.spath)
        else:
            print("\n    (None)")
        print("\nThese files were deleted in the new package "
              "because their parent dir was deleted:")
        if self.ignore_del_files:
            for f in self.ignore_del_files:
                print("    " + f.spath)
        else:
            print("\n    (None)")
        print("\nThese files are added in the new package:")
        if self.FL_2_isolated_files:
            for f in self.FL_2_isolated_files:
                print("    " + f.spath)
        else:
            print("\n    (None)")

    def __dir_compare(self):
        self.diff_dirs = []
        FL_1_dirs_cp = sorted(
            [d for d in self.FL_1.dirlist if d.spath not in self.FL_1_isolated_dirs_spaths],
            key=lambda x: x.spath
        )
        FL_2_dirs_cp = sorted(
            [d for d in self.FL_2.dirlist if d.spath not in self.FL_2_isolated_dirs_spaths],
            key=lambda x: x.spath
        )
        assert len(FL_1_dirs_cp) == len(FL_2_dirs_cp)
        for i in range(len(FL_1_dirs_cp)):
            if FL_1_dirs_cp[i] != FL_2_dirs_cp[i]:
                print("Dir %s has changed!" % FL_1_dirs_cp[i].spath)
                self.diff_dirs.append(FL_2_dirs_cp[i])

    def __file_compare(self):
        self.diff_files = []
        FL_1_files_cp = sorted(
            [f for f in self.FL_1 if f.spath not in self.FL_1_isolated_files_spaths],
            key=lambda x: x.spath
        )
        FL_2_files_cp = sorted(
            [f for f in self.FL_2 if f.spath not in self.FL_2_isolated_files_spaths],
            key=lambda x: x.spath
        )
        assert len(FL_1_files_cp) == len(FL_2_files_cp)
        for i in range(len(FL_1_files_cp)):
            if FL_1_files_cp[i] != FL_2_files_cp[i]:
                print("File %s has changed!" % FL_1_files_cp[i].spath)
                self.diff_files.append((FL_1_files_cp[i], FL_2_files_cp[i]))

def compare_build_prop(dic_1, dic_2):
    if not (isinstance(dic_1, dict) and isinstance(dic_2, dict)):
        raise ValueError("The parameters must be Dict!")
    all_kv = set(dic_1.keys()) & set(dic_2.keys())
    # 优先使用"ro.build.version.incremental"属性值来验证Rom 因为重复的可能性很小
    # 其次考虑"ro.build.date.utc"
    first_k = ["ro.build.version.incremental", "ro.build.date.utc"]
    for k in first_k:
        if (k in all_kv) and (dic_1[k] != dic_2[k]):
            return k, dic_1[k], dic_2[k]
    sel_kv = [(k, dic_1[k], dic_2[k]) for k in all_kv if dic_1[k] != dic_2[k]]
    if not sel_kv:
        raise Exception("Seems that these two Roms are the same.")
    print("We could not find a suitable attribute.")
    print("You need to choose one manually.\n")
    for num, kv in enumerate(sel_kv):
        print("Option %s:" % num+1)
        print("  Key      : %s\n"
              "  Old Value: %s\n"
              "  New Value: %s\n"
              % kv)
    while True:
        try:
            sel = int(input("Please enter the number: "))
        except:
            print("\nError number! Try again please.\n")
        else:
            if sel in range(1, len(sel_kv) + 1):
                return sel_kv[sel-1]
            print("\nError number! Try again please.\n")
