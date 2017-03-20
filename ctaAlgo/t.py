# -*- coding: utf-8 -*-
from Tkinter import *

global t
global root

def yes():
    global t
    t = 'Yes'

    root.destroy()

def no():
    global t
    t = 'No'
    root.destroy()

def main():
    global t
    global root

    root = Tk()
    root.title("hello world")
    root.geometry('300x200')


    t = None

    l = Label(root, text=u"弹窗确认模块", font=("Arial", 12))
    l.pack(side=TOP)

    Button(root, text="Yes", command=yes).pack(side=LEFT)
    Button(root, text="No", command=no).pack(side=RIGHT)
    print t
    root.mainloop()
    print t


if __name__ == '__main__':
    main()
