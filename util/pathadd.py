import winreg
import sys, win32gui, win32con

def reg_key(tree, path, varname):
    return r'%s\%s:%s' % (tree, path, varname) 

def reg_entry(tree, path, varname, value):
    return '%s=%s' % (reg_key(tree, path, varname), value)

def query_value(key, varname):
    value, type_id = winreg.QueryValueEx(key, varname)
    return value

def yield_all_entries(tree, path, key):
    i = 0
    while True:
        try:
            n,v,t = winreg.EnumValue(key, i)
            yield reg_entry(tree, path, n, v)
            i += 1
        except OSError:
            break ## Expected, this is how iteration ends.

def notify_windows(action, tree, path, varname, value):
    win32gui.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')
    print("---%s %s" % (action, reg_entry(tree, path, varname, value)), file=sys.stderr)

def manage_registry_env_vars(varname=None, value=None):
    reg_keys = [
        ('HKEY_LOCAL_MACHINE', r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'),
        ('HKEY_CURRENT_USER', r'Environment'),
    ]
    for (tree_name, path) in reg_keys:
        tree = eval('winreg.%s'%tree_name)
        try:
            with winreg.ConnectRegistry(None, tree) as reg:
                with winreg.OpenKey(reg, path, 0, winreg.KEY_ALL_ACCESS) as key:
                    # if value in query_value(key, varname)

                    if not varname:
                        for regent in yield_all_entries(tree_name, path, key):
                            print(regent)
                    else:
                        if not value:
                            if varname.startswith('-'):
                                varname = varname[1:]
                                value = query_value(key, varname)
                                winreg.DeleteValue(key, varname)
                                notify_windows("Deleted", tree_name, path, varname, value)
                                break  ## Don't propagate into user-tree.
                            else:
                                value = query_value(key, varname)
                                print(reg_entry(tree_name, path, varname, value))
                        else:
                            if varname.startswith('+'):
                                varname = varname[1:]
                                value = query_value(key, varname) + ';' + value
                            winreg.SetValueEx(key, varname, 0, winreg.REG_EXPAND_SZ, value)
                            notify_windows("Updated", tree_name, path, varname, value)
                            break  ## Don't propagate into user-tree.
        except PermissionError as ex:
            print("!!!Cannot access %s due to: %s" % 
                    (reg_key(tree_name, path, varname), ex), file=sys.stderr)
        except FileNotFoundError as ex:
            print("!!!Cannot find %s due to: %s" % 
                    (reg_key(tree_name, path, varname), ex), file=sys.stderr)

if __name__=='__main__':
    args = sys.argv
    argc = len(args)
    if argc > 3:
        print(__doc__.format(prog=args[0]), file=sys.stderr)
        sys.exit()

    manage_registry_env_vars(*args[1:])