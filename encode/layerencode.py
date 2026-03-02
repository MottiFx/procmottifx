import gc
import os
import time
from PIL import Image
import av
import moderngl as mgl
import numpy as np
import sounddevice as sd

from libmottifx.fx.basics.normal import BasicShader
from procmottifx.systems.parsing.cacheframe import FOLDER_CHCFRM, add_chcfrm, get_chcfrm, list_chcfrm
from procmottifx.systems.projects.getproject import get_projectfile
from procmottifx.systems.protos import schema_pb2 as sch
from libmottifx.compact.effect import LISTAUDFX, LISTEFFECT
from guimottifx.utils.configediting import ConfigAudio, ConfigFrame, ConfigTimeLine
from guimottifx.utils.currentprj import CurrentPrj
from guimottifx.utils.signal import UTILSLAYER, UTILSLAYERSETTINGS, UTILSPREVIEW
import threading

class ManageThread:
    def __init__(self):        
        startframe = threading.Event()
        triggerevent = threading.Event()
        audioevent = threading.Event()
        self.resetevent = threading.Event()
        self.lyc = LayerEncode(startframe,triggerevent,audioevent,self.resetevent)
        self.framework = threading.Thread(target=self.lyc._renderloop,daemon=True)
        self.audiowork = threading.Thread(target=self.lyc._renderaudio,daemon=True)

    def safetyproc(self):
        self.resetevent.set()
        self.framework.start()
        self.audiowork.start()

    def stopproc(self):
        self.resetevent.clear()
        #* dont use .join() it will make you gui crash
        # self.framework.join()
        # self.audiowork.join()


class LayerEncode:
    def __init__(self,startframe,triggerevent,audioevent,resetevent):        
        self.triggerevent = triggerevent
        self.audioevent = audioevent
        self.startframe = startframe
        self.resetevent = resetevent

        UTILSLAYER.setup_frame.connect(self._startframe)
        UTILSLAYER.setup_frame.connect(self._renderrequest)
        UTILSLAYER.pos_layer.connect(self._renderrequest)
        UTILSPREVIEW.pos_frame.connect(self._renderrequest)
        UTILSLAYERSETTINGS.layerset_pos_frame.connect(self._renderrequest)
        UTILSPREVIEW.audio_play.connect(self._audiorequest)
        UTILSPREVIEW.audio_pause.connect(self._audiopause)
        # UTILSPREVIEW.pausecache.connect(self._clearcache)

        # khusus cache image dikirim ke ram
        self.cacheimg = {}
        self.activecontainer = {}
        self.audiocontainer = {}
    
    def _startframe(self):
        self.startframe.set()

    def _renderrequest(self):
        self.triggerevent.set()

    def _audiorequest(self):
        self.audioevent.set()
    
    def _audiopause(self):
        sd.stop()
    
    def _renderloop(self):
        self.vertex_shader = '''
        #version 450

        in vec2 in_vert;
        in vec2 in_tex;
        out vec2 v_uv;
        void main() {
            gl_Position = vec4(in_vert, 0.0, 1.0);
            v_uv = in_tex;
        }

        '''
        self.ctx = mgl.create_standalone_context()
        # self.ctx.gc_mode = "auto" # testing
        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = (mgl.SRC_ALPHA,mgl.ONE_MINUS_SRC_ALPHA)
        self.ctx.clear(0,0,0,1)

        # print(CurrentPrj.pathfile)

        quad = np.array([
        -1, -1, 0, 0,
         1, -1, 1, 0,
        -1,  1, 0, 1,
        -1,  1, 0, 1,
         1, -1, 1, 0,
         1,  1, 1, 1,
        ], dtype='f4')

        self.vbo = self.ctx.buffer(quad.tobytes())

        while True:
            if self.startframe.is_set(): break
            print("loop")
            time.sleep(0.1)

        # print(ConfigTimeLine.DURATION)
        
        projf,_ = get_projectfile()
        project = projf.project

        outw,outh = int(project.width/ConfigFrame.LOSSLES),int(project.height/ConfigFrame.LOSSLES) # mengecilkan untukmencoba lossles

        self.mainbyt = bytearray(outw * outh * 4)

        self.final_fbo = self.ctx.framebuffer(color_attachments=self.ctx.texture((outw,outh),4))
        self.final_fbo.clear(0,0,0,1)

        self.first_tmp = self.ctx.framebuffer(color_attachments=self.ctx.texture((outw,outh),4))
        self.second_tmp = self.ctx.framebuffer(color_attachments=self.ctx.texture((outw,outh),4))
        
        while self.resetevent.is_set():
            self.triggerevent.wait()
            if ConfigTimeLine.PREVIEW:
                currentframe = int(round(ConfigTimeLine.CURRENTPOS * ConfigTimeLine.FPS))
                currentframe += 1
                ConfigTimeLine.CURRENTPOS = currentframe / ConfigTimeLine.FPS
                UTILSPREVIEW.preview_pos.emit()
            self.layercapture()
            self.triggerevent.clear()

        self.final_fbo.release()
        self.first_tmp.release()
        self.second_tmp.release()
        self.ctx.release()
        self._clearcache()

    def _clearcache(self):
        for _,cont in self.activecontainer.items():
            try: cont.close()
            except Exception as _: ... #
        

        self.activecontainer.clear()
        self.cacheimg.clear()
        # gc.collect() # bikin bug force close
        # self.ctx.gc() # bikin bug force close

    def _renderaudio(self):
        sd.default.samplerate = ConfigAudio.SAMPLE_RATE
        while True:
            if self.startframe.is_set(): break
            print("audio")
            time.sleep(0.1)
        while self.resetevent.is_set():
            self.audioevent.wait()
            sd.stop()
            _audarr = self.bufferaudio()
            conf = ConfigTimeLine
            # jaga-jaga biar pas walaupun dh  pasti
            _timepos = round(conf.CURRENTPOS * conf.FPS) / conf.FPS
            _lr = 1/ConfigAudio.CHANNELS
            _timepos = int(round((_timepos+_lr) * ConfigAudio.SAMPLE_RATE))
            sd.play(_audarr[_timepos:])
            del _audarr
            # with wave.open("outputs_filsename.wav", 'wb') as wf:
            #     wf.setnchannels(2)
            #     wf.setsampwidth(2)
            #     wf.setframerate(ConfigAudio.SAMPLE_RATE)
            #     clipaud = np.clip(_audarr,-1,1)
            #     clipint = clipaud * 32767.0
            #     wf.writeframes(clipint.astype(np.int16).tobytes()) 
            self.audioevent.clear()

    #* Sytem Layer Video and Image Already Clear, 

    def encodeimage(self,path):
            if path in self.cacheimg:
                return self.cacheimg[path]
            img = None
            try:
                img = Image.open(path).convert("RGBA")
                imgarry = np.array(img,dtype=np.uint8)
                self.cacheimg[path] = imgarry # buth kompress
                return imgarry
            finally: 
                if img: img.close()
        
    def encodevideo(self,path,time):
        if path not in self.activecontainer:
            self.activecontainer[path] = av.open(path) 
        container = self.activecontainer[path]

        try:
            streams = container.streams.video[0]
        except Exception as _: return None
        # round cocok untuk mengakurasikan frame/buffer
        time_to_sec = int(round(time / streams.time_base))
        # print(time_to_sec)

        container.seek(time_to_sec,stream=streams)

        get_frame = next((frame.to_ndarray(format="rgba") for frame in container.decode(streams) if frame.pts >= time_to_sec),None) #* perlu coba pakai konsep generator di music.py, apakah bisa atau tidak, untuk menghindari bottleneck juga

        # yield get_frame
        return get_frame
    
    # Sytem Audio already clear but sometimes audio mis millisecond

    def encodeaudio(self,start_pos,end_pos,path):
        # if path not in self.audiocontainer:
        #     self.audiocontainer[path] = av.open(path)
        container = av.open(path)

        try:
            streams = container.streams.audio[0]
        except Exception as _: return None

        # target_timestamp = int(round(start_pos / streams.time_base))
        # container.seek(target_timestamp, stream=streams)

        resampler = av.AudioResampler(
            format='fltp', #* fltp = float 32 planar, flt = float 32 only
            layout='stereo',
            rate=ConfigAudio.SAMPLE_RATE,
        )

        list_sampler = (resampler.resample(frame) for frame in container.decode(streams) if start_pos <= frame.pts * streams.time_base <= end_pos)

        to_arr = np.concatenate([fr.to_ndarray() for resample in list_sampler for fr in resample],axis=1,dtype=np.float32)

        return to_arr
    
    def bufferaudio(self):
        projf,_ = get_projectfile()

        listlayer = [lyr for lyr in projf.layers if ConfigTimeLine.CURRENTPOS <= ConfigTimeLine.DURATION and lyr.typlyr in [sch.TYP_LYR_VIDEO,sch.TYP_LYR_AUDIO] and not lyr.visible]
        listlayer.sort(key=lambda lyr: lyr.order)

        blankaudio = np.zeros((ConfigAudio.CHANNELS,int(round(ConfigTimeLine.DURATION * ConfigAudio.SAMPLE_RATE))),dtype=np.float32)

        for lyr in listlayer:
            _pathlayer = next(pth.path for pth in projf.assets if pth.uid == lyr.asset_uids)
            _audio = self.encodeaudio(lyr.realstart,lyr.realend,_pathlayer)
            # DONT USE TRANSPOSE IN EACH AUDIO, USE .T IN LAST SYSTEM 
            # _audio = _audio.T
            if _audio is None: continue
            
            # dipaskan sesuai latency channelsnya
            start_pos = int(round(lyr.start * (ConfigAudio.SAMPLE_RATE)))
            end_pos = start_pos + _audio.shape[1]

            # if _audio.shape[0] != ConfigAudio.CHANNELS:  _audio.T
            # print(f'shape 0: {_audio.shape[0]}')
            # print(f'shape 1:{_audio.shape[1]}')
            # print(f'start: {start_pos}')
            # print(f'end:{end_pos}')

            if end_pos > blankaudio.shape[1]: end_pos = blankaudio.shape[1]

            total_sample = end_pos - start_pos
            if total_sample > _audio.shape[1]: 
                total_sample = _audio.shape[1]
                end_pos = start_pos + _audio.shape[1]
            # print(total_sample)
            for audfx in [lyr for lyr in lyr.effects if lyr.typfx in [sch.TypFx.TYP_FX_BASICAUDIO]]:
                _funcfx = next(eff["func"] for eff in LISTAUDFX if eff["typfx"] == audfx.typfx)
                data = _funcfx(_audio[:,:total_sample],audfx.variables).render()

            blankaudio[:,start_pos:end_pos] += data

        #! This only use integer to effect this, because integer have limit, but float not
        #* recommended is use float, because already stable
        # normalize volume
        # max_vol = np.max(np.abs(blankaudio))
        # max_int16 = 32767

        # if max_vol > max_int16: mixed = (blankaudio * (max_int16/max_vol)).astype(np.int16)
        # else: mixed = blankaudio.astype(np.int16)

        #* ⁣⁣⁢CHANGE TO _RENDERAUDIO BECAUSE TIMEPOS IS ALWAYS UPDATE⁡
        # _perfps = 2.0 / ConfigTimeLine.FPS
        # time_pos = int(round((ConfigTimeLine.CURRENTPOS+_perfps) * ConfigAudio.SAMPLE_RATE))
        # mixed = mixed[time_pos:,:]

        #? ⁡⁣⁣⁢YEAH THIS, USE .T IN LAST SETTINGS⁡
        #? because can make your computer so heavy ,when you spam use this
        return blankaudio.T


    # TODO: ‍‍Layer Video and Image system⁡​

    def blankframe(self,outw,outh):
        data = np.zeros((outh,outw,4),dtype=np.uint8)
        data[:,:,3] = 255
        return data
    
    def layercapture(self): # NOSONAR
        projf,_ = get_projectfile()
        project = projf.project

        # TODO: Need feature change preview like -> 100%,50%,10% #NOSONAR
        # TODO: Need fix framebuffer,untuk penyesuaian effect lyr agar effectnya hanya terkena di size texturenya saja
        #* buat fix -> 2 fbo untuk semua effect tetapi sesuai size texture asli dan 2 fbo untuk menyesuaikan size preview [mungkin gini]
        outw,outh = int(project.width/ConfigFrame.LOSSLES),int(project.height/ConfigFrame.LOSSLES) # mengecilkan untukmencoba lossles
        # outw,outh = int(project.width/ConfigFrame.LOSSLES)//10,int(project.height/ConfigFrame.LOSSLES)//10 # mengecilkan untukmencoba lossles

        _frame_idx = int(round(ConfigTimeLine.CURRENTPOS * ConfigTimeLine.FPS)) # key_time
        # _noround = int(ConfigTimeLine.CURRENTPOS * ConfigTimeLine.FPS)

        # print(f'Round: {_frame_idx}, Not Round: {_noround}')

        #* slow version                 
        # listframe = list_chcfrm()
        # _ckframe = next((True for lf in listframe if _frame_idx == int(lf.split('.')[0])),False)
        #? different in millisecond i think
        conf = CurrentPrj
        folder = f"{conf.folderfile}/{FOLDER_CHCFRM}"
        filepath =f"{folder}/{_frame_idx}.chfr" 
        _ckframe = os.path.exists(filepath)

        active_layer = [lyr for lyr in projf.layers if lyr.start <= ConfigTimeLine.CURRENTPOS <= lyr.end and lyr.typlyr != sch.TypLyr.TYP_LYR_AUDIO and not lyr.visible]
        active_layer.sort(key=lambda lyr: lyr.order)

        if not _ckframe:
            if active_layer:
                for layer in active_layer:
                    _pathlayer = next(pth.path for pth in projf.assets if pth.uid == layer.asset_uids)

                    if layer.typlyr == sch.TypLyr.TYP_LYR_IMAGE:
                        _frame = self.encodeimage(_pathlayer)
                    elif layer.typlyr == sch.TypLyr.TYP_LYR_VIDEO:
                        _second = layer.realend - (layer.end - ConfigTimeLine.CURRENTPOS)
                        _frame = self.encodevideo(_pathlayer,_second)
                    
                    # gunakan blank frame dari fbo nya langsung jika frame tidak ada
                    if _frame is None: continue
                    
                    # _tex = self.ctx.texture((_frame.shape[1],_frame.shape[0]),4,_frame.tobytes())
                    #* gunakan memoryview karena dia bisa membaca bytes dengan mengakses buffer
                    _tex = self.ctx.texture((_frame.shape[1],_frame.shape[0]),4,memoryview(_frame))
                    _tex.filter = (mgl.NEAREST,mgl.NEAREST)
                    # _tex.repeat_y = False
                    # _tex.repeat_x = False
                    # _tex.build_mipmaps()
                    
                    _cur_tex = _tex
                    # print(_cur_tex.size)
                    _effx = ([ly for ly in layer.effects if ly.typfx != sch.TypFx.TYP_FX_BASICAUDIO])

                    _ls_tmp  = [self.first_tmp,self.second_tmp]
                    _idx_tmp = 0
                    
                    for fx in _effx:
                        tmp_fbo = _ls_tmp[_idx_tmp]
                        tmp_fbo.clear()

                        _fx_class = next(eff["func"] for eff in LISTEFFECT if eff["typfx"] == fx.typfx)

                        _fx_use = _fx_class(_cur_tex,self.ctx,self.vertex_shader,self.vbo,(outw,outh),fx.variables,ConfigTimeLine.CURRENTPOS)

                        _fx_use.render(tmp_fbo)
                        self.ctx.memory_barrier(barriers=mgl.ALL_BARRIER_BITS) # testing untuk pastiin shader
                        _cur_tex = tmp_fbo.color_attachments[0]
                        _idx_tmp = 1 - _idx_tmp

                    _comb = BasicShader(_cur_tex,self.ctx,self.vertex_shader,self.vbo)
                    _comb.render(self.final_fbo)
                    
                    # tmp_fbo.color_attachments[0].release()
                    # tmp_fbo.release()
                    _tex.release()
                    del _tex

                # self.cachefbo[_frame_idx] = self.final_fbo.read(components=4) # rgb lebih lambat dibanding rba
                # self.final_fbo.read() cukup bisa

                # gunakan memoryview karena dia bisa membaca bytes dengan mengakses buffer atau arraynya langsung
                self.final_fbo.read_into(self.mainbyt,components=4) # f1 = uint8
                raw_data = memoryview(self.mainbyt)

                add_chcfrm(raw_data,_frame_idx)
                # raw_data = data
                # self.final_fbo.color_attachments[0].release()
                # self.final_fbo.release()
                # del self.final_fbo
                self.final_fbo.clear(0,0,0,1)
            else:
                if ConfigTimeLine.PREVIEW:
                    self._clearcache()
                data = self.blankframe(outw,outh)
                raw_data = memoryview(data)
            
        else:
            if ConfigTimeLine.PREVIEW:
                self._clearcache()
            raw_data = memoryview(get_chcfrm(_frame_idx))
        
        if not ConfigFrame.SETUPFRAME:
            ConfigFrame.SETUPFRAME = True
            UTILSPREVIEW.setup_frame.emit(raw_data,outw,outh)
        else:
            UTILSPREVIEW.change_frame.emit(raw_data,outw,outh)

        if not ConfigTimeLine.PREVIEW: 
            #* just use in this line, because its so danger if we cant use this
            self._clearcache()
            # gc.collect() bikin bug force close dan tidak bisa dijalankan dua kali secara bergantian ,harus dalams satu program
