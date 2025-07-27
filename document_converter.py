#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档格式转换模块

本模块提供多种文档格式转换功能，包括：
1. DOC到DOCX转换
2. 各种文档格式之间的转换
3. 支持多种转换引擎（pypandoc、LibreOffice等）
4. 临时文件管理
5. 转换质量验证

作者: AI Assistant
创建时间: 2025-01-15
"""

import os
import sys
import logging
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime


class DocumentConverterError(Exception):
    """文档转换异常类"""
    pass


class DocumentConverter:
    """文档转换器类
    
    支持多种文档格式转换，优先使用最佳可用转换引擎
    """
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        初始化文档转换器
        
        Args:
            temp_dir: 临时文件目录，如果为None则使用系统默认临时目录
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.available_engines = self._detect_available_engines()
        self.setup_logging()
        
        # 支持的转换映射
        self.conversion_map = {
            '.doc': ['.docx', '.pdf', '.txt', '.html', '.md'],
            '.docx': ['.pdf', '.txt', '.html', '.md', '.doc'],
            '.pdf': ['.txt', '.html', '.md'],
            '.txt': ['.docx', '.pdf', '.html', '.md'],
            '.md': ['.docx', '.pdf', '.html', '.txt'],
            '.html': ['.docx', '.pdf', '.txt', '.md'],
            '.rtf': ['.docx', '.pdf', '.txt', '.html', '.md'],
            '.odt': ['.docx', '.pdf', '.txt', '.html', '.md']
        }
        
    def setup_logging(self) -> None:
        """设置日志记录，仅输出到控制台"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
        logging.info("文档转换器初始化完成")
        
    def _detect_available_engines(self) -> Dict[str, bool]:
        """检测可用的转换引擎（使用缓存避免重复检测）"""
        global _engines_cache, _engines_cache_timestamp
        
        # 检查缓存是否有效（5分钟内）
        current_time = datetime.now().timestamp()
        if (_engines_cache is not None and 
            _engines_cache_timestamp is not None and 
            current_time - _engines_cache_timestamp < 300):  # 5分钟缓存
            logging.debug("使用缓存的引擎检测结果")
            return _engines_cache.copy()
        
        logging.info("开始检测可用的转换引擎...")
        engines = {
            'pypandoc': False,
            'libreoffice': False,
            'unoconv': False,
            'pywin32': False,
            'antiword': False
        }
        
        # 检测pypandoc
        try:
            import pypandoc
            # 检查pandoc是否可用
            pypandoc.get_pandoc_version()
            engines['pypandoc'] = True
            logging.info("✓ 检测到pypandoc引擎")
        except Exception as e:
            logging.debug(f"pypandoc不可用: {e}")
        
        # 检测LibreOffice
        try:
            # 检查常见的LibreOffice安装路径
            libreoffice_paths = [
                'soffice',  # Linux/Mac
                'libreoffice',  # Linux
                r'C:\Program Files\LibreOffice\program\soffice.exe',  # Windows
                r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',  # Windows 32-bit
            ]
            
            for path in libreoffice_paths:
                try:
                    result = subprocess.run([path, '--version'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        engines['libreoffice'] = True
                        logging.info(f"✓ 检测到LibreOffice: {path}")
                        break
                except Exception:
                    continue
        except Exception as e:
            logging.debug(f"LibreOffice检测失败: {e}")
        
        # 检测unoconv
        try:
            result = subprocess.run(['unoconv', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                engines['unoconv'] = True
                logging.info("✓ 检测到unoconv引擎")
        except Exception as e:
            logging.debug(f"unoconv不可用: {e}")
        
        # 检测pywin32 (仅Windows)
        if os.name == 'nt':
            try:
                import win32com.client
                engines['pywin32'] = True
                logging.info("✓ 检测到pywin32引擎（Windows专用）")
            except Exception as e:
                logging.debug(f"pywin32不可用: {e}")
        
        # 检测antiword (主要用于Linux/Mac)
        try:
            result = subprocess.run(['antiword', '-v'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                engines['antiword'] = True
                logging.info("✓ 检测到antiword引擎")
        except Exception as e:
            logging.debug(f"antiword不可用: {e}")
        
        # 缓存结果
        _engines_cache = engines.copy()
        _engines_cache_timestamp = current_time
        
        # 输出检测摘要
        available_engines = [name for name, available in engines.items() if available]
        if available_engines:
            logging.info(f"引擎检测完成，可用引擎: {', '.join(available_engines)}")
        else:
            logging.warning("未检测到任何可用的转换引擎")
        
        return engines
    
    def can_convert(self, source_format: str, target_format: str) -> bool:
        """
        检查是否支持指定格式转换
        
        Args:
            source_format: 源格式（如'.doc'）
            target_format: 目标格式（如'.docx'）
            
        Returns:
            是否支持转换
        """
        source_format = source_format.lower()
        target_format = target_format.lower()
        
        return (source_format in self.conversion_map and 
                target_format in self.conversion_map[source_format])
    
    def convert_document(self, source_path: str, target_format: str, 
                        output_path: Optional[str] = None, 
                        engine: Optional[str] = None) -> str:
        """
        转换文档格式
        
        Args:
            source_path: 源文件路径
            target_format: 目标格式（如'.docx'）
            output_path: 输出文件路径，如果为None则生成临时文件
            engine: 指定转换引擎，如果为None则自动选择
            
        Returns:
            转换后的文件路径
            
        Raises:
            DocumentConverterError: 转换失败时抛出
        """
        source_path = Path(source_path)
        if not source_path.exists():
            raise DocumentConverterError(f"源文件不存在: {source_path}")
        
        source_format = source_path.suffix.lower()
        target_format = target_format.lower()
        if not target_format.startswith('.'):
            target_format = '.' + target_format
        
        # 检查是否支持转换
        if not self.can_convert(source_format, target_format):
            raise DocumentConverterError(
                f"不支持从{source_format}转换到{target_format}")
        
        # 生成输出路径
        if output_path is None:
            output_path = self._generate_temp_path(source_path.stem, target_format)
        else:
            output_path = Path(output_path)
        
        # 选择转换引擎
        if engine is None:
            engine = self._select_best_engine(source_format, target_format)
        
        logging.info(f"开始转换: {source_path} -> {output_path} (引擎: {engine})")
        
        try:
            if engine == 'simple_rename':
                self._convert_with_simple_rename(source_path, output_path, target_format)
            elif engine == 'pypandoc':
                self._convert_with_pypandoc(source_path, output_path, target_format)
            elif engine == 'libreoffice':
                self._convert_with_libreoffice(source_path, output_path, target_format)
            elif engine == 'unoconv':
                self._convert_with_unoconv(source_path, output_path, target_format)
            elif engine == 'pywin32':
                self._convert_with_pywin32(source_path, output_path, target_format)
            elif engine == 'antiword':
                self._convert_with_antiword(source_path, output_path, target_format)
            else:
                raise DocumentConverterError(f"不支持的转换引擎: {engine}")
            
            # 验证转换结果
            if not output_path.exists() or output_path.stat().st_size == 0:
                raise DocumentConverterError("转换失败：输出文件为空或不存在")
            
            logging.info(f"转换成功: {output_path}")
            return str(output_path)
            
        except Exception as e:
            # 清理失败的输出文件
            if output_path.exists():
                try:
                    output_path.unlink()
                except Exception:
                    pass
            raise DocumentConverterError(f"文档转换失败: {e}")
    
    def _generate_temp_path(self, base_name: str, extension: str) -> Path:
        """生成临时文件路径"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"{base_name}_{timestamp}{extension}"
        return Path(self.temp_dir) / filename
    
    def _select_best_engine(self, source_format: str, target_format: str) -> str:
        """选择最佳转换引擎"""
        # DOC到DOCX转换优先级
        if source_format == '.doc' and target_format == '.docx':
            # Windows系统优先使用pywin32
            if os.name == 'nt' and self.available_engines['pywin32']:
                return 'pywin32'
            # 优先使用简单重命名方法（适用于某些.doc文件实际上是.docx格式）
            return 'simple_rename'
        
        # 其他转换优先使用pypandoc
        if self.available_engines['pypandoc']:
            return 'pypandoc'
        elif self.available_engines['libreoffice']:
            return 'libreoffice'
        elif self.available_engines['unoconv']:
            return 'unoconv'
        elif os.name == 'nt' and self.available_engines['pywin32']:
            return 'pywin32'
        elif self.available_engines['antiword'] and target_format in ['.txt', '.docx']:
            return 'antiword'
        
        raise DocumentConverterError("没有可用的转换引擎")
    
    def _convert_with_simple_rename(self, source_path: Path, output_path: Path, target_format: str) -> None:
        """使用简单重命名进行转换（适用于.doc实际上是.docx格式的情况）"""
        try:
            # 首先检查源文件是否真的是zip格式（即伪装的docx文件）
            if target_format == '.docx':
                try:
                    import zipfile
                    # 尝试以zip格式打开源文件
                    with zipfile.ZipFile(str(source_path), 'r') as zip_file:
                        # 检查是否包含docx的基本结构
                        required_files = ['[Content_Types].xml', 'word/document.xml']
                        zip_contents = zip_file.namelist()
                        for required_file in required_files:
                            if required_file not in zip_contents:
                                raise Exception(f"缺少必要文件: {required_file}")
                    
                    # 如果验证通过，说明这是一个伪装的docx文件，可以直接重命名
                    shutil.copy2(str(source_path), str(output_path))
                    logging.info(f"简单重命名转换完成（伪装的docx文件）: {source_path} -> {output_path}")
                    return
                    
                except Exception as e:
                    # 如果不是zip格式，说明是真正的传统.doc文件，需要使用其他转换方法
                    logging.info(f"源文件不是zip格式（真正的.doc文件）: {e}，使用其他转换方法")
                    self._fallback_convert(source_path, output_path, target_format)
                    return
            
            # 对于其他格式的简单重命名
            shutil.copy2(str(source_path), str(output_path))
            logging.info(f"简单重命名转换完成: {source_path} -> {output_path}")
                    
        except Exception as e:
            raise DocumentConverterError(f"简单重命名转换失败: {e}")
    
    def _fallback_convert(self, source_path: Path, output_path: Path, target_format: str) -> None:
        """备用转换方法"""
        # 尝试其他可用的转换引擎
        if self.available_engines['libreoffice']:
            self._convert_with_libreoffice(source_path, output_path, target_format)
        elif self.available_engines['unoconv']:
            self._convert_with_unoconv(source_path, output_path, target_format)
        elif self.available_engines['pypandoc']:
            self._convert_with_pypandoc(source_path, output_path, target_format)
        elif os.name == 'nt' and self.available_engines['pywin32']:
            self._convert_with_pywin32(source_path, output_path, target_format)
        elif self.available_engines['antiword'] and target_format in ['.txt', '.docx']:
            self._convert_with_antiword(source_path, output_path, target_format)
        else:
            raise DocumentConverterError("所有转换方法都失败了")
    
    def _convert_with_pypandoc(self, source_path: Path, output_path: Path, target_format: str) -> None:
        """使用pypandoc进行转换"""
        try:
            import pypandoc
            
            # 移除点号前缀
            pandoc_format = target_format.lstrip('.')
            
            # 特殊格式映射
            format_map = {
                'docx': 'docx',
                'doc': 'doc',
                'pdf': 'pdf',
                'txt': 'plain',
                'md': 'markdown',
                'html': 'html'
            }
            
            pandoc_format = format_map.get(pandoc_format, pandoc_format)
            
            # 执行转换 - 兼容新版本pypandoc
            try:
                # 新版本API
                pypandoc.convert_file(
                    str(source_path),
                    pandoc_format,
                    outputfile=str(output_path)
                )
            except TypeError:
                # 旧版本API兼容
                pypandoc.convert_file(
                    str(source_path),
                    pandoc_format,
                    outputfile=str(output_path)
                )
            
        except ImportError:
            raise DocumentConverterError("pypandoc未安装")
        except Exception as e:
            raise DocumentConverterError(f"pypandoc转换失败: {e}")
    
    def _convert_with_pywin32(self, source_path: Path, output_path: Path, target_format: str) -> None:
        """使用pywin32进行转换（Windows专用）"""
        try:
            import win32com.client
            
            # 创建Word应用程序对象
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False  # 不显示Word界面
            
            try:
                # 打开.doc文件
                doc = word.Documents.Open(str(source_path.absolute()))
                
                # 格式映射
                format_map = {
                    '.docx': 16,  # wdFormatXMLDocument
                    '.pdf': 17,   # wdFormatPDF
                    '.txt': 2,    # wdFormatText
                    '.html': 8,   # wdFormatHTML
                    '.rtf': 6     # wdFormatRTF
                }
                
                file_format = format_map.get(target_format)
                if not file_format:
                    raise DocumentConverterError(f"pywin32不支持格式: {target_format}")
                
                # 另存为指定格式
                doc.SaveAs2(str(output_path.absolute()), FileFormat=file_format)
                doc.Close()
                
            finally:
                word.Quit()
                
        except ImportError:
            raise DocumentConverterError("pywin32未安装")
        except Exception as e:
            raise DocumentConverterError(f"pywin32转换失败: {e}")
    
    def _convert_with_antiword(self, source_path: Path, output_path: Path, target_format: str) -> None:
        """使用antiword进行转换（提取文本后保存为简单docx）"""
        try:
            # 使用antiword提取文本
            result = subprocess.run(['antiword', str(source_path)], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise DocumentConverterError(f"antiword提取文本失败: {result.stderr}")
            
            text_content = result.stdout
            
            if target_format == '.docx':
                # 创建简单的docx文件
                try:
                    from docx import Document
                    doc = Document()
                    
                    # 将文本按段落分割并添加到文档
                    paragraphs = text_content.split('\n')
                    for para in paragraphs:
                        if para.strip():  # 跳过空行
                            doc.add_paragraph(para)
                    
                    doc.save(str(output_path))
                    
                except ImportError:
                    raise DocumentConverterError("python-docx未安装，无法创建docx文件")
                except Exception as e:
                    raise DocumentConverterError(f"创建docx文件失败: {e}")
            
            elif target_format == '.txt':
                # 直接保存为文本文件
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
            
            else:
                raise DocumentConverterError(f"antiword不支持输出格式: {target_format}")
                
        except subprocess.TimeoutExpired:
            raise DocumentConverterError("antiword转换超时")
        except Exception as e:
            raise DocumentConverterError(f"antiword转换失败: {e}")
    
    def _convert_with_libreoffice(self, source_path: Path, output_path: Path, target_format: str) -> None:
        """使用LibreOffice进行转换"""
        try:
            # 查找LibreOffice可执行文件
            soffice_paths = [
                'soffice',
                'libreoffice',
                r'C:\Program Files\LibreOffice\program\soffice.exe',
                r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
            ]
            
            soffice_cmd = None
            for path in soffice_paths:
                try:
                    result = subprocess.run([path, '--version'], 
                                          capture_output=True, timeout=5)
                    if result.returncode == 0:
                        soffice_cmd = path
                        break
                except Exception:
                    continue
            
            if not soffice_cmd:
                raise DocumentConverterError("找不到LibreOffice可执行文件")
            
            # 格式映射
            format_map = {
                '.docx': 'docx',
                '.doc': 'doc',
                '.pdf': 'pdf',
                '.txt': 'txt',
                '.html': 'html',
                '.odt': 'odt'
            }
            
            lo_format = format_map.get(target_format)
            if not lo_format:
                raise DocumentConverterError(f"LibreOffice不支持格式: {target_format}")
            
            # 创建输出目录
            output_dir = output_path.parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 执行转换
            cmd = [
                soffice_cmd,
                '--headless',
                '--convert-to', lo_format,
                '--outdir', str(output_dir),
                str(source_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                raise DocumentConverterError(f"LibreOffice转换失败: {result.stderr}")
            
            # LibreOffice会生成与源文件同名但扩展名不同的文件
            expected_output = output_dir / f"{source_path.stem}{target_format}"
            if expected_output.exists() and expected_output != output_path:
                shutil.move(str(expected_output), str(output_path))
            
        except subprocess.TimeoutExpired:
            raise DocumentConverterError("LibreOffice转换超时")
        except Exception as e:
            raise DocumentConverterError(f"LibreOffice转换失败: {e}")
    
    def _convert_with_unoconv(self, source_path: Path, output_path: Path, target_format: str) -> None:
        """使用unoconv进行转换"""
        try:
            # 格式映射
            format_map = {
                '.docx': 'docx',
                '.doc': 'doc',
                '.pdf': 'pdf',
                '.txt': 'txt',
                '.html': 'html',
                '.odt': 'odt'
            }
            
            uno_format = format_map.get(target_format)
            if not uno_format:
                raise DocumentConverterError(f"unoconv不支持格式: {target_format}")
            
            # 创建输出目录
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 执行转换
            cmd = [
                'unoconv',
                '-f', uno_format,
                '-o', str(output_path),
                str(source_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                raise DocumentConverterError(f"unoconv转换失败: {result.stderr}")
            
        except subprocess.TimeoutExpired:
            raise DocumentConverterError("unoconv转换超时")
        except Exception as e:
            raise DocumentConverterError(f"unoconv转换失败: {e}")
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """获取支持的转换格式映射"""
        return self.conversion_map.copy()
    
    def get_available_engines(self) -> Dict[str, bool]:
        """获取可用的转换引擎"""
        return self.available_engines.copy()
    
    def _check_libreoffice(self) -> Dict[str, Any]:
        """检查LibreOffice状态"""
        result = {
            'available': False,
            'path': None,
            'version': None,
            'error': None
        }
        
        try:
            # 检查常见的LibreOffice安装路径
            libreoffice_paths = [
                'soffice',  # Linux/Mac
                'libreoffice',  # Linux
                r'C:\Program Files\LibreOffice\program\soffice.exe',  # Windows
                r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',  # Windows 32-bit
            ]
            
            for path in libreoffice_paths:
                try:
                    process_result = subprocess.run([path, '--version'], 
                                          capture_output=True, text=True, timeout=10)
                    if process_result.returncode == 0:
                        result['available'] = True
                        result['path'] = path
                        result['version'] = process_result.stdout.strip()
                        return result
                except Exception:
                    continue
            
            result['error'] = 'LibreOffice未安装或不在系统PATH中'
            
        except Exception as e:
            result['error'] = f'检查LibreOffice时出错: {str(e)}'
        
        return result
    
    def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """清理临时文件
        
        Args:
            max_age_hours: 文件最大保留时间（小时）
            
        Returns:
            清理的文件数量
        """
        cleaned_count = 0
        temp_path = Path(self.temp_dir)
        
        if not temp_path.exists():
            return 0
        
        current_time = datetime.now().timestamp()
        max_age_seconds = max_age_hours * 3600
        
        try:
            for file_path in temp_path.iterdir():
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        try:
                            file_path.unlink()
                            cleaned_count += 1
                            logging.info(f"清理临时文件: {file_path}")
                        except Exception as e:
                            logging.warning(f"清理文件失败 {file_path}: {e}")
        except Exception as e:
            logging.error(f"清理临时文件时出错: {e}")
        
        return cleaned_count


# 全局转换器实例和引擎检测缓存
_converter_instance = None
_engines_cache = None
_engines_cache_timestamp = None


def get_converter() -> DocumentConverter:
    """获取全局文档转换器实例"""
    global _converter_instance
    if _converter_instance is None:
        _converter_instance = DocumentConverter()
    return _converter_instance


def install_conversion_dependencies() -> Dict[str, bool]:
    """安装转换依赖库
    
    Returns:
        安装结果字典
    """
    results = {
        'pypandoc': False,
        'pandoc': False,
        'python-docx': False,
        'pywin32': False
    }
    
    try:
        # 安装pypandoc
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pypandoc'], 
                      check=True, capture_output=True)
        results['pypandoc'] = True
        logging.info("pypandoc安装成功")
        
        # 尝试安装pandoc
        try:
            import pypandoc
            pypandoc.download_pandoc()
            results['pandoc'] = True
            logging.info("pandoc安装成功")
        except Exception as e:
            logging.warning(f"pandoc自动安装失败: {e}")
            logging.info("请手动安装pandoc: https://pandoc.org/installing.html")
        
    except Exception as e:
        logging.error(f"pypandoc依赖安装失败: {e}")
    
    try:
        # 安装python-docx
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'python-docx'], 
                      check=True, capture_output=True)
        results['python-docx'] = True
        logging.info("python-docx安装成功")
    except Exception as e:
        logging.error(f"python-docx安装失败: {e}")
    
    # Windows系统尝试安装pywin32
    if os.name == 'nt':
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'pywin32'], 
                          check=True, capture_output=True)
            results['pywin32'] = True
            logging.info("pywin32安装成功")
        except Exception as e:
            logging.error(f"pywin32安装失败: {e}")
    
    return results