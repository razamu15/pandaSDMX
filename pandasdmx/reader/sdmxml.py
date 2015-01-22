# encoding: utf-8


from pandasdmx.utils import DictLike
from pandasdmx import model
from .common import Reader
from lxml import objectify
from lxml.etree import XPath



 
class SDMXMLReader(Reader):

    
    """
    Read SDMX-ML 2.1 and expose it as instances from pandasdmx.model
    """
    
    _nsmap = {
            'com': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common',
            'str': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure',
            'mes': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message'
    }

    def initialize(self, source):
        root = objectify.parse(source).getroot()
        self.response = model.Response(self, root)
        return self.response 
    
    _model_map = {
        'header' : (XPath('mes:Header[1]', namespaces = _nsmap), model.Header), 
        'annotations' : (XPath('com:Annotations/com:Annotation', 
                             namespaces = _nsmap), model.Annotation),
        'codelists' : (XPath('mes:Structures/str:Codelists/str:Codelist', 
                             namespaces = _nsmap), model.Codelist),
                  'codes': (XPath('str:Code', 
                             namespaces = _nsmap), model.Code),  
                  'conceptschemes' : (XPath('mes:Structures/str:Concepts/str:ConceptScheme', 
                             namespaces = _nsmap), model.ConceptScheme),
        'concepts' : (XPath('str:Concept', 
                             namespaces = _nsmap), model.Concept),
        'categoryschemes' : (XPath('mes:Structures/str:CategorySchemes/str:CategoryScheme', 
                             namespaces = _nsmap), model.CategoryScheme),
        'categories': (XPath('str:Category', 
                             namespaces = _nsmap), model.Category),  
        'dataflows' : (XPath('mes:Structures/str:Dataflows/str:Dataflow', 
                             namespaces = _nsmap), model.DataflowDefinition),
        'datastructures' : (XPath('mes:Structures/str:DataStructures/str:DataStructure', 
                             namespaces = _nsmap), model.DataStructureDefinition),
        'dimdescriptor' : (XPath('str:DataStructureComponents/str:DimensionList', 
                             namespaces = _nsmap), model.DimensionDescriptor),
        'dimensions': (XPath('str:Dimension', 
                             namespaces = _nsmap), model.Dimension),
        'time_dimension': (XPath('str:TimeDimension', 
                             namespaces = _nsmap), model.TimeDimension),
        'measure_dimension': (XPath('str:MeasureDimension', 
                             namespaces = _nsmap), model.MeasureDimension),
        'measures' : (XPath('str:DataStructureComponents/str:MeasureList', 
                             namespaces = _nsmap), model.MeasureDescriptor),
        'measure_items' : (XPath('str:PrimaryMeasure', 
                             namespaces = _nsmap), model.PrimaryMeasure), 
        'attributes' : (XPath('str:DataStructureComponents/str:AttributeList', 
                             namespaces = _nsmap), model.AttributeDescriptor),
                  'attribute_items' : (XPath('str:Attribute', 
                             namespaces = _nsmap), model.DataAttribute),
    } 
        
        
    def read(self, name, elem):
        path, cls = self._model_map[name]
        return cls(self, path(elem)[0])
     
     
    def read_dict(self, name, elem):
        '''
        return dict mapping IDs to item instances from model.
        elem must be DictLike
        '''
        path, cls = self._model_map[name]
        return DictLike({e.get('id') : cls(self, e) for e in path(elem)})
        

         
             
    
    def header_id(self, elem):
        return elem.ID[0].text 

    def identity(self, elem):
        return elem.get('id')
    
    def urn(self, elem):
        return elem.get('urn')

    def uri(self, elem):
        return elem.get('uri')
        
        
    def agencyID(self, elem):
        return elem.get('agencyID')
    
    
    def _international_string(self, elem, tagname):
        languages = elem.xpath('com:{0}/@xml:lang'.format(tagname), 
                               namespaces = self._nsmap)
        strings = elem.xpath('com:{0}/text()'.format(tagname), 
                             namespaces = self._nsmap)
        return DictLike(zip(languages, strings))

    def description(self, elem):
        return self._international_string(elem, 'Description') 
        
    def name(self, elem):
        return self._international_string(elem, 'Name') 
        

    def header_prepared(self, elem):
        return elem.Prepared[0].text # convert this to datetime obj?
        
    def header_sender(self, elem):
        return DictLike(elem.Sender.attrib)

    def header_error(self, elem):
        try:
            return DictLike(elem.Error.attrib)
        except AttributeError: return None
                     
    def _items(self, elem, path, model_cls):
        '''
        return dict mapping IDs to item instances from model.
        elem must be an item scheme
        '''    
        return DictLike({e.get('id') : model_cls(self, e) for e in elem.xpath(path, 
                    namespaces = self._nsmap)}) 
                     
        
        
    def isfinal(self, elem):
        return bool(elem.get('isFinal')) 
        
    def structure(self, elem):
        '''
        return content of a model.Structure.  
        '''
        return model.Structure(self, elem.xpath('str:Structure', 
                                                namespaces = self._nsmap))
    
    def concept_id(self, elem):
        # called by model.Component.concept
        c_id = elem.xpath('str:ConceptIdentity/Ref/@id', 
                          namespaces = self._nsmap)[0]
        parent_id = elem.xpath('str:ConceptIdentity/Ref/@maintainableParentID',
                               namespaces = self._nsmap)[0]
        return self.response.conceptschemes[parent_id][c_id]
        
    def position(self, elem):
        # called by model.Dimension
        return int(elem.get('position')) 
    
    def localrepr(self, elem):
        node = elem.xpath('str:LocalRepresentation',
                          namespaces = self._nsmap)[0]
        enum = node.xpath('str:Enumeration/Ref/@id',
                          namespaces = node.nsmap)
        if enum: enum = self.response.codelists[enum[0]]
        else: enum = None
        return model.Representation(self, node, enum = enum)
    
    def assignment_status(self, elem):
        return elem.get('assignmentStatus')
        
    def attr_relationship(self, elem):
        return elem.xpath('*/Ref/@id')
         
         
    def parse_series(self, source):
        """
        generator to parse data from xml. Iterate over series
        """
        CodeTuple = None
        generic_ns = '{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic}'
        series_tag = generic_ns + 'Series'
        serieskey_tag = series_tag + 'Key'
        value_tag = generic_ns + 'Value'
        obs_tag = generic_ns + 'Obs'
        obsdim_tag = generic_ns + 'ObsDimension'
        obsvalue_tag = generic_ns + 'ObsValue'
        attributes_tag = generic_ns + 'Attributes' 
        context = lxml.etree.iterparse(source, tag = series_tag)
        
        for _, series in context: 
            raw_dates, raw_values, raw_status = [], [], []
            
            for elem in series.iterchildren():
                if elem.tag == serieskey_tag:
                    code_keys, code_values = [], []
                    for value in elem.iter(value_tag):
                        if not CodeTuple: code_keys.append(value.get('id')) 
                        code_values.append(value.get('value'))
                elif elem.tag == obs_tag:
                    for elem1 in elem.iterchildren():
                        observation_status = 'A'
                        if elem1.tag == obsdim_tag:
                            dimension = elem1.get('value')
                            # Prepare time spans such as Q1 or S2 to make it parsable
                            suffix = dimension[-2:]
                            if suffix in time_spans:
                                dimension = dimension[:-2] + time_spans[suffix]
                            raw_dates.append(dimension) 
                        elif elem1.tag == obsvalue_tag:
                            value = elem1.get('value')
                            raw_values.append(value)
                        elif elem1.tag == attributes_tag:
                            for elem2 in elem1.iter(".//"+generic_ns+"Value[@id='OBS_STATUS']"):
                                observation_status = elem2.get('value')
                            raw_status.append(observation_status)
            if not CodeTuple:
                CodeTuple = make_namedtuple(code_keys) 
            codes = CodeTuple._make(code_values)
            series.clear()
            yield codes, raw_dates, raw_values, raw_status 
    
    