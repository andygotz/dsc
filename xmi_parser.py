"""
Parsing utility for Tango .xmi files.

"""

from lxml import etree
import models
import os
import logging
import re

logger = logging.getLogger(__name__)

pogoDslDataTypes = models.DS_COMMAND_DATATYPES

class TangoXmiParser:
    """
        Parses .xmi files generated by Pogo
    """

    def __init__(self, file_path):
        self.file_path = file_path
        self.tree = etree.parse(self.file_path)

        # classes related elements
        self.classes_elements = self.tree.findall('classes')

    def get_device_server(self):
        """
        Return a device server model from the parsed file
        :return: device server object created from the file
        """

        name = os.path.splitext(os.path.basename(self.file_path))[0]
        description = None
        ds_license = None
        description_element = self.classes_elements[0].find('description')
        if description_element is not None:
            description = description_element.attrib['description']
            ds_license = description_element.attrib['license']

        return models.DeviceServer(name=name, descritpition=description, license=ds_license)

    def get_device_classes(self):
        """
        Parse the .xmi file for classes definitions
        :return: list of DeviceClass objects
        """
        cls = []

        for cl in self.classes_elements:
            name = cl.attrib.get('name')
            description_element = self.classes_elements[0].find('description')
            description = ''
            lic = ''
            class_copyright = ''
            language = ''
            if description_element is not None:
                description = description_element.attrib.get('description')
                lic = description_element.attrib.get('license')
                class_copyright = description_element.attrib.get('copyright')
                language = description_element.attrib.get('language')
            cls.append(models.DeviceClass(name=name, description=description, license=lic, language=language))

        return cls

    def get_device_class_info(self, cl):
        """
        Return info related to class cl
        :param cl: name or DeviceClass object for which the info has to be retrived
        :return: DeviceClassInfo objec
        """
        # find class name
        if isinstance(cl, str):
            name = cl
        elif isinstance(cl, models.DeviceClass):
            name = cl.name
        elif hasattr(cl, 'attrib'):
            name = cl.attrib.get('name')
        else:
            name = str(cl)

        # find class element in the .xmi
        class_element = next((x for x in self.classes_elements if x.attrib.get('name') == name), None)
        if class_element is None:
            logger.error("Class of provided name does not exist in the xmi file.")
            return None

        # find related description element
        description_element = class_element.find('description')
        if description_element is None:
            logger.error("No description for the class in the XMI file.")
            return None

        # then identification element
        identification_element = description_element.find('identification')
        if identification_element is None:
            logger.error("No identification for the class in the XMI file.")
            return None

        # parse for email (there are two ways of coding it in the .xmi file)
        contact_email_attrib = identification_element.attrib.get('contact')
        author = identification_element.attrib.get('author')
        email_domain = identification_element.attrib.get('emailDomain')
        if contact_email_attrib is None:
            contact_email = "%s@%s" % (author, email_domain)
        else:
            email_re = re.search(r'at (.*) - (.*)', contact_email_attrib)
            contact_email = "%s@%s" % (email_re.group(2), email_re.group(1))

        # get other info frm the element
        class_family = identification_element.attrib.get('classFamily')
        platform = identification_element.attrib.get('platform')
        bus = identification_element.attrib.get('bus')
        manufacturer = identification_element.attrib.get('manufacturer')
        product = identification_element.attrib.get('reference')
        # key words are listed in their own tag
        kw_elements = identification_element.findall('keyWords')
        key_words = ','.join([kw.text for kw in kw_elements])

        # return a model object build of  information retrieved
        return models.DeviceClassInfo(
            xmi_file=self.file_path,
            contact_email=contact_email,
            class_family=class_family,
            platform=platform,
            bus=bus,
            manufacturer=manufacturer,
            key_words=key_words,
            product_reference=product
        )

    def get_device_attributes(self, cl):
        """
        Retrun list of attributes for class cl
        :param cl: name or DeviceClass object
        :return: list of DeviceAttribute obejcts
        """

        # find class name
        if isinstance(cl, str):
            name = cl
        elif isinstance(cl, models.DeviceClass):
            name = cl.name
        elif hasattr(cl, 'attrib'):
            name = cl.attrib.get('name')
        else:
            name = str(cl)

        # find class element in the .xmi
        class_element = next((x for x in self.classes_elements if x.attrib.get('name') == name), None)
        if class_element is None:
            logger.error("Class of provided name does not exist in the xmi file.")
            return None

        # find attribute elements
        attributes_list = []
        attributes_elements = class_element.findall('attributes')
        # parse all elements
        for attribute_element in attributes_elements:

            attribute_name = attribute_element.attrib.get('name')
            attribute_type = attribute_element.attrib.get('attType')
            attribute_data_type_element = attribute_element.find('dataType')
            if attribute_data_type_element is None:
                logger.error('An attribute has no dataType info in .xmi file.')
                attribute_data_type = 'unknown'
            else:
                attribute_xsi_type =   attribute_data_type_element.attrib.get('xsi:type').split(':')[1]
                attribute_data_type = pogoDslDataTypes.get(attribute_xsi_type)

            attribute_description = ''
            attribute_properties_element = attribute_element.find('properties')
            if attribute_properties_element is not None:
                attribute_description = attribute_properties_element.attrib.get('description')

            # append attribute to the list
            attributes_list.append(models.DeviceAttribute(name=attribute_name,
                                                          descritpion=attribute_description,
                                                          data_type=attribute_data_type,
                                                          attribute_type=attribute_type))

        # return list
        return attributes_list

    def get_device_commands(self, cl):
        """
        Retrun list of commands for class cl
        :param cl: name or DeviceClass object
        :return: list of DeviceCommand objects
        """
        # find class name
        if isinstance(cl, str):
            name = cl
        elif isinstance(cl, models.DeviceClass):
            name = cl.name
        elif hasattr(cl, 'attrib'):
            name = cl.attrib.get('name')
        else:
            name = str(cl)

        # find class element in the .xmi
        class_element = next((x for x in self.classes_elements if x.attrib.get('name') == name), None)
        if class_element is None:
            logger.error("Class of provided name does not exist in the xmi file.")
            return None

        # find attribute elements
        commands_list = []
        commands_elements = class_element.findall('commands')
        # parse all elements
        for command_element in commands_elements:
            # basic command information
            command_name = command_element.attrib.get('name')
            command_description = command_element.attrib.get('description')
            # data types and descriptions
            argin_element = command_element.find('argin')
            if argin_element is not None:
                input_xsi_type = argin_element.find('type').attrib.get('xsi:type').split(':')[1]
                input_type = pogoDslDataTypes.get(input_xsi_type)
                input_description = argin_element.attrib.get('description')

            argout_element = command_element.find('argout')
            if argout_element is not None:
                argout_xsi_type = argout_element.find('type').attrib.get('xsi:type').split(':')[1]
                output_type = pogoDslDataTypes.get(input_xsi_type)
                output_description = argout_element.attrib.get('description')

            # append attribute to the list
            commands_list.append(models.DeviceCommand(name=command_name,
                                                      descritpion=command_description,
                                                      input_type=input_type,
                                                      input_description=input_description,
                                                      output_type=output_type,
                                                      output_description=output_description))

        # return list
        return commands_list

    def get_device_properties(self, cl):
        """
        Retrun list of class and device properties for class cl
        :param cl: name or DeviceClass object
        :return: list of DeviceProperty objects
        """

        # find class name
        if isinstance(cl, str):
            name = cl
        elif isinstance(cl, models.DeviceClass):
            name = cl.name
        elif hasattr(cl, 'attrib'):
            name = cl.attrib.get('name')
        else:
            name = str(cl)

        # find class element in the .xmi
        class_element = next((x for x in self.classes_elements if x.attrib.get('name') == name), None)
        if class_element is None:
            logger.error("Class of provided name does not exist in the xmi file.")
            return None

        # find property elements
        properties_list = []
        properties_elements = class_element.findall('deviceProperties') + class_element.findall('classProperties')
        # parse all elements
        for property_element in properties_elements:
            # basic command information
            property_name = property_element.attrib.get('name')
            property_description = property_element.attrib.get('description')
            # data type
            property_xsi_type = property_element.find('type').attrib.get('xsi:type').split(':')[1]
            property_type = pogoDslDataTypes.get(property_xsi_type)

            # append attribute to the list
            properties_list.append(models.DeviceProperty(name=property_name,
                                                         descritpion=property_description,
                                                         property_type=property_type,
                                                         is_class_property=(property_element.tag == 'classProperty')))

        # return list
        return properties_list
