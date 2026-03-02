import threading
import av
import numpy as np
from PIL import Image
from procmottifx.systems.protos import schema_pb2 as sch
from guimottifx.utils.configediting import ConfigAudio, ConfigRender, ConfigTimeLine
from libmottifx.compact.effect import LISTAUDFX, LISTEFFECT
from libmottifx.fx.basics.normal import BasicShader
import moderngl as mgl
from procmottifx.systems.projects.getproject import get_projectfile
from guimottifx.utils.signal import UTILSRENDER

class ManageRender:
    def __init__(self):
        self.closeEvent = threading.Event()
        self.layerDcd = LayerDecode(self.closeEvent)

    def renderProc(self,codec,bitrate,folder,name):
        self.framework = threading.Thread(target=self.layerDcd._renderloop,daemon=True,args=(codec,bitrate,folder,name))
        self.framework.start()

    def stopProc(self):
        self.closeEvent.set()

class LayerDecode:
    def __init__(self,closeEvent):
        self.closeEvent = closeEvent
        self.cacheimg = {}
        self.activecontainer = {}
        self.audiocontainer = {}

    def _renderloop(self,codec,bitrate,folder,name):
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

        projf,_ = get_projectfile()
        project = projf.project

        outw,outh = int(project.width),int(project.height)
        total_frame = int(round(ConfigTimeLine.DURATION * ConfigTimeLine.FPS))
        print(total_frame)

        self.mainbyt = bytearray(outw * outh * 4)

        self.final_fbo = self.ctx.framebuffer(color_attachments=self.ctx.texture((outw,outh),4))
        self.final_fbo.clear(0,0,0,1)

        self.first_tmp = self.ctx.framebuffer(color_attachments=self.ctx.texture((outw,outh),4))
        self.second_tmp = self.ctx.framebuffer(color_attachments=self.ctx.texture((outw,outh),4))

        _outpath = f"{folder}/{name}.mp4"
        _final_container = av.open(_outpath,mode="w",format="mp4")
        
        _av_video = _final_container.add_stream(codec,rate=int(ConfigTimeLine.FPS))
        _av_video.width = outw
        _av_video.height = outh
        _av_video.pix_fmt = "yuv444p"
        _av_video.bit_rate = bitrate * 1000000

        _av_audio = _final_container.add_stream(_final_container.default_audio_codec,rate=ConfigAudio.SAMPLE_RATE)
        _av_audio.layout = "stereo"

        UTILSRENDER.RENDERSTART.emit()
        timepos = 0
        idx_frm = 0
        while not self.closeEvent.is_set():
            for fidx in range(total_frame):
                if self.closeEvent.is_set(): break
                buff = self.layerExport(outw,outh,timepos)
                v_frame = av.VideoFrame.from_bytes(buff.tobytes(),outw,outh,"rgba")
                v_frame.pts = fidx
                for packet in _av_video.encode(v_frame):
                    _final_container.mux(packet)

                _secpos = int(round(timepos * ConfigTimeLine.FPS))
                _secpos += 1
                idx_frm += 1
                timepos = _secpos / ConfigTimeLine.FPS
                print(timepos)
                prgtxt = int((idx_frm / total_frame) * 100)
                UTILSRENDER.PROGTEXT.emit(f"{prgtxt}%")

            _audbuff = self.bufferaudio()
            _audframe = av.AudioFrame.from_ndarray(_audbuff,format="fltp",layout="stereo")
            _audframe.sample_rate = ConfigAudio.SAMPLE_RATE

            for packet in _av_audio.encode(_audframe):
                if self.closeEvent.is_set(): break
                _final_container.mux(packet)

            for packet in _av_video.encode(): 
                if self.closeEvent.is_set(): break
                _final_container.mux(packet)
            for packet in _av_audio.encode(): 
                if self.closeEvent.is_set(): break
                _final_container.mux(packet)

            self.closeEvent.set()
            
        _final_container.close()
        self.final_fbo.release()
        self.first_tmp.release()
        self.second_tmp.release()
        self.ctx.release()
        UTILSRENDER.PROGTEXT.emit("Finish")
        UTILSRENDER.RENDERSTART.emit()
        ConfigRender.status = False

    def encodeimage(self,path):
        if path in self.cacheimg:
            return self.cacheimg[path]
        img = None
        try:
            img = Image.open(path).convert("RGBA")
            imgarry = np.array(img,dtype=np.uint8)
            self.cacheimg[path] = imgarry
            return imgarry
        finally: 
            if img:img.close()
        
    def encodevideo(self,path,time):
        if path not in self.activecontainer:
            self.activecontainer[path] = av.open(path)
        container = self.activecontainer[path]

        try:
            streams = container.streams.video[0]
        except Exception as _: return None
        
        # round cocok untuk mengakurasikan frame/buffer
        time_to_sec = int(round(time / streams.time_base))
        container.seek(time_to_sec,stream=streams)

        get_frame = next((frame.to_ndarray(format="rgba") for frame in container.decode(streams) if frame.pts >= time_to_sec),None) #* perlu coba pakai konsep generator di music.py, apakah bisa atau tidak, untuk menghindari bottleneck juga

        # yield get_frame
        return get_frame

    def encodeaudio(self,start_pos,end_pos,path):
        container = av.open(path)

        try:
            streams = container.streams.audio[0]
        except Exception as _: return None

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

        listlayer = [lyr for lyr in projf.layers if  lyr.typlyr in [sch.TYP_LYR_VIDEO,sch.TYP_LYR_AUDIO] and not lyr.visible]
        listlayer.sort(key=lambda lyr: lyr.order)

        blankaudio = np.zeros((ConfigAudio.CHANNELS,int(round(ConfigTimeLine.DURATION * ConfigAudio.SAMPLE_RATE))),dtype=np.float32)

        for lyr in listlayer:
            _pathlayer = next(pth.path for pth in projf.assets if pth.uid == lyr.asset_uids)
            _audio = self.encodeaudio(lyr.realstart,lyr.realend,_pathlayer)
            if _audio is None: continue
            
            # dipaskan sesuai latency channelsnya
            start_pos = int(round(lyr.start * (ConfigAudio.SAMPLE_RATE)))
            end_pos = start_pos + _audio.shape[1]

            if end_pos > blankaudio.shape[1]: end_pos = blankaudio.shape[1]

            total_sample = end_pos - start_pos
            if total_sample > _audio.shape[1]: 
                total_sample = _audio.shape[1]
                end_pos = start_pos + _audio.shape[1]

            for audfx in [lyr for lyr in lyr.effects if lyr.typfx in [sch.TypFx.TYP_FX_BASICAUDIO]]:
                _funcfx = next(eff["func"] for eff in LISTAUDFX if eff["typfx"] == audfx.typfx)
                data = _funcfx(_audio[:,:total_sample],audfx.variables).render()

            blankaudio[:,start_pos:end_pos] += data

        return blankaudio
        
    def blankframe(self,outw,outh):
        data = np.zeros((outh,outw,4),dtype=np.uint8)
        data[:,:,3] = 255
        return data

    def layerExport(self,outw,outh,timepos):
        projf,_ = get_projectfile()

        active_layer = [lyr for lyr in projf.layers if lyr.start <= timepos <= lyr.end and lyr.typlyr != sch.TypLyr.TYP_LYR_AUDIO and not lyr.visible]
        active_layer.sort(key=lambda lyr: lyr.order)

        if active_layer:
            for layer in active_layer:
                _pathlayer = next(pth.path for pth in projf.assets if pth.uid == layer.asset_uids)

                _frame = None
                if layer.typlyr == sch.TypLyr.TYP_LYR_IMAGE:
                    _frame = self.encodeimage(_pathlayer)
                elif layer.typlyr == sch.TypLyr.TYP_LYR_VIDEO:
                    _second = layer.realend - (layer.end - timepos)
                    _frame = self.encodevideo(_pathlayer,_second)

                if _frame is None: continue

                _tex = self.ctx.texture((_frame.shape[1],_frame.shape[0]),4,memoryview(_frame))
                _tex.filter = (mgl.LINEAR,mgl.LINEAR)

                _cur_tex = _tex
                _effx = ([ly for ly in layer.effects if ly.typfx != sch.TypFx.TYP_FX_BASICAUDIO])

                _ls_tmp = [self.first_tmp,self.second_tmp]
                _idx_tmp = 0

                for fx in _effx:
                    tmp_fbo = _ls_tmp[_idx_tmp]
                    tmp_fbo.clear()

                    _fx_class = next(eff["func"] for eff in LISTEFFECT if eff["typfx"] == fx.typfx)
                    _fx_use = _fx_class(_cur_tex,self.ctx,self.vertex_shader,self.vbo,(outw,outh),fx.variables,timepos)

                    _fx_use.render(tmp_fbo)

                    _cur_tex = tmp_fbo.color_attachments[0]
                    _idx_tmp = 1 - _idx_tmp

                _comb = BasicShader(_cur_tex,self.ctx,self.vertex_shader,self.vbo)
                _comb.render(self.final_fbo)

                _tex.release()
                del _tex

            self.final_fbo.read_into(self.mainbyt,components=4)
            raw_data = memoryview(self.mainbyt)

            self.final_fbo.clear(0,0,0,1)
        else:
            data = self.blankframe(outw,outh)
            raw_data = memoryview(data)

        return raw_data

