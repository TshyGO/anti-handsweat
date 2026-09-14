"""Small local GUI. No image uploads or remote API calls."""
from __future__ import annotations
import json
from platform_paths import discover_exiftool
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

ROOT = Path(__file__).resolve().parent

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title('涂层图像准备  V0.1.1  |  方法开发版')
        root.geometry('1060x740')
        root.minsize(880, 650)
        self.files: list[Path] = []
        self.profile: dict | None = None
        self.q: queue.Queue = queue.Queue()
        self.buttons = []
        self.last_run: Path | None = None
        self.is_busy = False
        root.protocol('WM_DELETE_WINDOW', self.on_close)
        main = ttk.Frame(root, padding=16); main.pack(fill='both', expand=True)
        ttk.Label(main, text='RAW → 固定解码 → 分析 TIFF ＋ 元数据', font=('',16,'bold')).pack(anchor='w')
        ttk.Label(main, text='练习与方法开发工具。当前不自动配准、不修正曝光、不判定涂层合格，也不计算印迹面积。', wraplength=980).pack(anchor='w',pady=(8,12))
        row = ttk.Frame(main); row.pack(fill='x')
        self.button(row,'① 选择 RAW（可多选）',self.choose_files).pack(side='left')
        self.button(row,'清空列表',self.clear).pack(side='left',padx=8)
        self.count = ttk.Label(row,text='尚未选择文件'); self.count.pack(side='left')
        self.listbox = tk.Listbox(main, height=6, selectmode='extended')
        self.listbox.pack(fill='x',pady=8)
        cfg = ttk.LabelFrame(main,text='② 固定配置',padding=10); cfg.pack(fill='x',pady=5)
        bar=ttk.Frame(cfg);bar.pack(fill='x')
        self.button(bar,'从一张参考 RAW 建立配置',self.reference).pack(side='left')
        self.button(bar,'载入配置 JSON',self.load_profile).pack(side='left',padx=8)
        self.button(bar,'保存配置 JSON',self.save_profile).pack(side='left')
        self.profile_label=ttk.Label(cfg,text='未设置。参考照片的白平衡仅用于固定流程，不代表已完成光源校准。',wraplength=940)
        self.profile_label.pack(anchor='w',pady=(8,0))
        options=ttk.LabelFrame(main,text='③ 输出与元数据',padding=10);options.pack(fill='x',pady=5)
        # Bundled resources can be read-only; never write inside an .app.
        output = Path.home()/'CoatingImaging'/'output' if getattr(sys, 'frozen', False) else ROOT/'output'
        self.out=tk.StringVar(value=str(output))
        self.exif=tk.StringVar(value=discover_exiftool(root=ROOT))
        ttk.Label(options,text='输出目录').grid(row=0,column=0,sticky='w')
        ttk.Entry(options,textvariable=self.out).grid(row=0,column=1,sticky='ew',padx=8)
        self.button(options,'选择',self.choose_output).grid(row=0,column=2)
        ttk.Label(options,text='ExifTool').grid(row=1,column=0,sticky='w',pady=8)
        ttk.Entry(options,textvariable=self.exif).grid(row=1,column=1,sticky='ew',padx=8)
        exif_buttons=ttk.Frame(options); exif_buttons.grid(row=1,column=2)
        self.button(exif_buttons,'选择程序',self.choose_exif).pack(side='left')
        self.button(exif_buttons,'自动查找',self.find_exif).pack(side='left',padx=(4,0))
        options.columnconfigure(1,weight=1)
        ttk.Label(options,text='未配置 ExifTool 时可输出练习图，但曝光等缺失字段将标为“未核查”，不能当作质控通过。',wraplength=940).grid(row=2,column=0,columnspan=3,sticky='w')
        self.rgb=tk.BooleanVar(value=True)
        ttk.Checkbutton(options,text='同时保存 RGB 16位线性 TIFF；始终保存单通道 Y 32位 TIFF',variable=self.rgb).grid(row=3,column=0,columnspan=3,sticky='w',pady=(8,0))
        actions=ttk.Frame(main);actions.pack(fill='x',pady=10)
        self.button(actions,'④ 批量转换',self.convert).pack(side='left')
        self.button(actions,'打开输出目录',self.open_output).pack(side='left',padx=8)
        self.button(actions,'打开说明',lambda:self.open_path(ROOT/('PACKAGED_README.html' if getattr(sys, 'frozen', False) else '00_Mac开始这里.html'))).pack(side='left')
        self.progress=ttk.Progressbar(actions,mode='indeterminate',length=180);self.progress.pack(side='right')
        self.logbox=tk.Text(main,height=8,wrap='word',state='disabled');self.logbox.pack(fill='both',expand=True)
        self.log('准备就绪。先选 RAW，再建立或载入固定配置。也可先用 demo 里的合成 TIFF 在 Fiji 练习。')
        root.after(100,self.poll)
    def button(self,parent,text,command):
        b=ttk.Button(parent,text=text,command=command);self.buttons.append(b);return b
    def log(self,s):
        self.logbox.configure(state='normal');self.logbox.insert('end',s+'\n');self.logbox.see('end');self.logbox.configure(state='disabled')
    def busy(self,value):
        self.is_busy = value
        for b in self.buttons:b.configure(state='disabled' if value else 'normal')
        if value:self.progress.start(15)
        else:self.progress.stop()
    def task(self,fn):
        self.busy(True)
        def job():
            try:fn()
            except Exception as e:self.q.put(('error',str(e)))
            finally:self.q.put(('done',None))
        threading.Thread(target=job,daemon=True).start()
    def poll(self):
        try:
            while True:
                what,val=self.q.get_nowait()
                if what=='log':self.log(val)
                elif what=='error':self.log('错误：'+val);messagebox.showerror('未完成',val)
                elif what=='profile':self.set_profile(val)
                elif what=='output':self.last_run=val;self.log('本批完成，请检查 batch_summary.csv 中的 FAILED / incomplete 项。\n'+str(val))
                elif what=='done':self.busy(False)
        except queue.Empty:pass
        self.root.after(100,self.poll)
    def choose_files(self):
        names=filedialog.askopenfilenames(title='选择原始 RAW',filetypes=[('RAW', ('*.arw','*.ARW','*.nef','*.NEF','*.cr2','*.CR2','*.cr3','*.CR3','*.dng','*.DNG','*.rw2','*.RW2','*.orf','*.ORF','*.raf','*.RAF')),('全部文件','*')])
        self.files=list(dict.fromkeys(self.files+[Path(n) for n in names]))
        self.listbox.delete(0,'end')
        for p in self.files:self.listbox.insert('end',str(p))
        self.count.configure(text=f'{len(self.files)} 个文件')
    def clear(self):
        self.files=[];self.listbox.delete(0,'end');self.count.configure(text='尚未选择文件')
    def choose_output(self):
        p=filedialog.askdirectory(title='选择输出目录')
        if p:self.out.set(p)
    def choose_exif(self):
        p=filedialog.askopenfilename(title='选择 exiftool 可执行文件（不要选择 pkg 安装包）', initialdir='/usr/local/bin' if sys.platform=='darwin' else str(ROOT/'tools'))
        if p:self.exif.set(p)
    def find_exif(self):
        path=discover_exiftool(root=ROOT)
        if path:
            self.exif.set(path); self.log('发现 ExifTool：'+path)
        else:
            messagebox.showinfo('未找到 ExifTool','先从官方安装 Mac 版 ExifTool，再点击自动查找。也可手动选择 exiftool 文件。')
    def on_close(self):
        if self.is_busy:
            messagebox.showinfo('正在处理','请先完成当前处理再关闭窗口，避免留下不完整的输出。')
            return
        self.root.destroy()
    def reference(self):
        p=filedialog.askopenfilename(title='选择本组参考 RAW：其白平衡与采集参数将成为固定基准')
        if not p:return
        exe=self.exif.get()
        def work():
            from pipeline import make_profile
            self.q.put(('log','读取参考 RAW；首次可能需要几秒。'))
            self.q.put(('profile',make_profile(Path(p),exe)))
        self.task(work)
    def set_profile(self,p):
        self.profile=p
        self.profile_label.configure(text='参考：'+Path(p['reference_file']).name+'\n固定 WB：'+str(p['user_wb'])+'；元数据：'+p['reference_exif']['status']+'；状态：方法开发，未标定')
        self.log('固定配置已就绪。后续文件共用这一组 WB，不逐张自动计算。')
    def load_profile(self):
        p=filedialog.askopenfilename(filetypes=[('JSON','*.json')])
        if p:
            try:
                obj=json.loads(Path(p).read_text(encoding='utf-8'))
                if obj.get('schema')!=1:raise ValueError('配置格式不支持。')
                self.set_profile(obj)
            except Exception as e:messagebox.showerror('载入失败',str(e))
    def save_profile(self):
        if self.profile is None:messagebox.showinfo('提示','先建立配置。');return
        p=filedialog.asksaveasfilename(defaultextension='.json',initialfile='fixed_profile_DEVELOPMENT.json')
        if p:Path(p).write_text(json.dumps(self.profile,ensure_ascii=False,indent=2),encoding='utf-8')
    def convert(self):
        if not self.files or self.profile is None:messagebox.showinfo('提示','需要选择 RAW，并建立或载入固定配置。');return
        files=self.files[:];out=Path(self.out.get());p=json.loads(json.dumps(self.profile));exe=self.exif.get();rgb=self.rgb.get()
        def work():
            from pipeline import process_batch
            self.q.put(('output',process_batch(files,out,p,exe,rgb,lambda s:self.q.put(('log',s)))))
        self.task(work)
    def open_output(self):self.open_path(self.last_run or Path(self.out.get()))
    def open_path(self,p):
        if not p.exists():messagebox.showinfo('提示','目录或文件尚未生成。');return
        if sys.platform=='win32':os.startfile(str(p))
        elif sys.platform=='darwin':subprocess.Popen(['open',str(p)])
        else:subprocess.Popen(['xdg-open',str(p)])

if __name__=='__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test':
        from packaged_smoke import run
        raise SystemExit(run(Path(sys.argv[2]), App, ROOT))
    root=tk.Tk()
    if sys.platform == 'darwin':
        try: root.createcommand('tk::mac::Quit', lambda: app.on_close())
        except tk.TclError: pass
    app=App(root)
    root.mainloop()
