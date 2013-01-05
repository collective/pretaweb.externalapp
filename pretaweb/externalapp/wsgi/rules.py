DEFAULT_DIAZO_RULES = """
<rules
    xmlns="http://namespaces.plone.org/diazo"
    xmlns:css="http://namespaces.plone.org/diazo/css"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xi="http://www.w3.org/2001/XInclude">

  <replace css:theme-children="#content" css:content-children="body" />

  <!-- Handle Elements with ACTION attribute -->
  <xsl:template match="*[@action]">
    <xsl:copy>

      <!-- Update ACTION attribute -->
      <xsl:choose>

        <!-- Absolute Link -->
        <xsl:when test="starts-with(@action, $external_app_url)">
          <xsl:attribute name="action"><xsl:value-of select="$app_url" /><xsl:value-of select="substring(@action,  string-length($external_app_url)+2)" /></xsl:attribute>
        </xsl:when>

        <!-- Relative Link starting from / -->
        <xsl:when test="starts-with(@action, '/')">
          <xsl:attribute name="action"><xsl:value-of select="$app_url" />.<xsl:value-of select="@action" /></xsl:attribute>
        </xsl:when>

        <!-- Else: only add app part -->
        <xsl:otherwise>
          <xsl:copy-of select="@action" />
        </xsl:otherwise>
      </xsl:choose>

      <xsl:copy-of select="@*[name()!='action']|node()" />
    </xsl:copy>
  </xsl:template>

  <!-- Handle Elements with HREF attribute -->
  <xsl:template match="*[@href][name()!='base']">
    <xsl:copy>

      <!-- Update HREF attribute -->
      <xsl:choose>

        <!-- Absolute Link -->
        <xsl:when test="starts-with(@href, $external_app_url)">
          <xsl:attribute name="href"><xsl:value-of select="$app_url" /><xsl:value-of select="substring(@href,  string-length($external_app_url)+2)" /></xsl:attribute>
        </xsl:when>

        <!-- Relative Link starting from / -->
        <xsl:when test="starts-with(@href, '/')">
          <xsl:attribute name="href"><xsl:value-of select="$app_url" />.<xsl:value-of select="@href" /></xsl:attribute>
        </xsl:when>

        <!-- Else: copy it as it is -->
        <xsl:otherwise>
          <xsl:copy-of select="@href" />
        </xsl:otherwise>

      </xsl:choose>

      <xsl:copy-of select="@*[name()!='href']|node()" />
    </xsl:copy>
  </xsl:template>

  <!-- Handle Elements with SRC attribute -->
  <xsl:template match="*[@src]">
    <xsl:copy>

      <!-- Update SRC attribute -->
      <xsl:choose>

        <!-- Absolute Link -->
        <xsl:when test="starts-with(@src, $external_app_url)">
          <xsl:attribute name="src"><xsl:value-of select="$app_url" /><xsl:value-of select="substring(@src,  string-length($external_app_url)+2)" /></xsl:attribute>
        </xsl:when>

        <!-- Relative Link starting from / -->
        <xsl:when test="starts-with(@src, '/')">
          <xsl:attribute name="src"><xsl:value-of select="$app_url" />.<xsl:value-of select="@src" /></xsl:attribute>
        </xsl:when>

        <!-- Else: copy it as it is -->
        <xsl:otherwise>
          <xsl:copy-of select="@src" />
        </xsl:otherwise>
      </xsl:choose>

      <xsl:copy-of select="@*[name()!='src']|node()" />
    </xsl:copy>
  </xsl:template>

</rules>
"""
