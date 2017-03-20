# -*- coding: utf-8 -*-
from Tkinter import *

root = Tk()
root.title("hello world")
root.geometry('300x300')  # 是x 不是*

l1 = Label(root, text=u"xls名：")
l1.pack()  # 这里的side可以赋值为LEFT  RTGHT TOP  BOTTOM
xls_text = StringVar()
xls = Entry(root, textvariable=xls_text)
xls_text.set(" ")
xls.pack()

l2 = Label(root, text=u"sheet名：")
l2.pack()  # 这里的side可以赋值为LEFT  RTGHT TOP  BOTTOM
sheet_text = StringVar()
sheet = Entry(root, textvariable=sheet_text)
sheet_text.set(" ")
sheet.pack()

l3 = Label(root, text=u"循环次数：")
l3.pack()  # 这里的side可以赋值为LEFT  RTGHT TOP  BOTTOM
loop_text = StringVar()
loop = Entry(root, textvariable=loop_text)
loop_text.set(" ")
loop.pack()

l4 = Label(root, text=u"休眠时间：")
l4.pack()  # 这里的side可以赋值为LEFT  RTGHT TOP  BOTTOM
sleep_text = StringVar()
sleep = Entry(root, textvariable=sleep_text)
sleep_text.set(" ")
sleep.pack()


def on_click():
    x = xls_text.get()
    s = sheet_text.get()
    l = loop_text.get()
    sl = sleep_text.get()
    # string = str(u"xls名：%s sheet名：%s 循环次数：%s 休眠时间：%s " % (x, s, l, sl))
    print(u"xls名：%s sheet名：%s 循环次数：%s 休眠时间：%s " % (x, s, l, sl))
    root.destroy()
    # messagebox.showinfo(title='aaa', message=string)


Button(root, text="press", command=on_click).pack()

root.mainloop()